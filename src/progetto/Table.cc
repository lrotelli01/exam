#include <algorithm> // <--- AGGIUNGI QUESTA RIGA
#include "Table.h"
Define_Module(Table);

Table::Table()
{
    activeReaders = 0;
    writeActive = false;
    totalServed = 0;
    totalReads = 0;
    totalWrites = 0;
    busyTimeStart = SIMTIME_ZERO;
    totalBusyTime = SIMTIME_ZERO;
    lastStateChange = SIMTIME_ZERO;
    maxQueueLength = 0;
    totalQueueLength = 0;
    queueLengthSamples = 0;
    totalWaitingTime = 0.0;
}

Table::~Table()
{
    // cancel and delete all pending service events
    for (cMessage* evt : serviceEvents) {
        cancelAndDelete(evt);
    }
    serviceEvents.clear();

    // delete all queued requests
    while (!requestQueue.empty()) {
        cMessage *m = requestQueue.front();
        requestQueue.pop();
        delete m;
    }
}

void Table::initialize()
{
    tableId = par("tableId");
    // numUsers is not strictly required here, but try to read it if set
    if (hasPar("numUsers"))
        numUsers = par("numUsers");
    else
        numUsers = -1;

    activeReaders = 0;
    writeActive = false;

    totalServed = 0;
    totalReads = 0;
    totalWrites = 0;

    busyTimeStart = SIMTIME_ZERO;
    totalBusyTime = SIMTIME_ZERO;
    lastStateChange = simTime();
    maxQueueLength = 0;
    totalQueueLength = 0;
    queueLengthSamples = 0;
    totalWaitingTime = 0.0;
    
    // Register signals (course-standard method)
    queueLengthSignal = registerSignal("queueLength");
    waitingTimeSignal = registerSignal("waitingTime");
    throughputSignal = registerSignal("throughput");
    utilizationSignal = registerSignal("utilization");

    EV_INFO << "Table " << tableId << " initialized" << endl;
}

void Table::handleMessage(cMessage *msg)
{
    // Distinguish between arrivals from users (original requests) and internal service completion events
    // We mark service completion events by their name starting with "serviceDone"

    if (strncmp(msg->getName(), "serviceDone", 11) == 0) {
        // Service completion for some original request
        cMessage *orig = (cMessage*) msg->getContextPointer();
        if (!orig) {
            EV_WARN << "serviceDone received with null contextPointer" << endl;
            removeEvent(msg);
            delete msg;
            return;
        }

        // Determine user id to send response
        long userId = -1;
        if (orig->hasPar("userId")) userId = orig->par("userId").longValue();

        bool isRead = (orig->getKind() == 0);

        // Create response message to send back to the user
        cMessage *resp = new cMessage("Response");
        resp->setKind(orig->getKind()); // preserve read/write kind
        // copy arrivalTime param so user can compute wait time
        if (orig->hasPar("arrivalTime")) {
            cMsgPar *p = new cMsgPar("arrivalTime");
            p->setDoubleValue(orig->par("arrivalTime").doubleValue());
            resp->addPar(p);
        }

        // send back to originating user via userOut[userId]
        if (userId >= 0) {
            send(resp, "userOut", (int)userId);
        } else {
            // If we don't know user id, just delete
            delete resp;
        }

        // Update stats
        totalServed++;
        if (isRead) totalReads++; else totalWrites++;

        EV_DEBUG << "Table " << tableId << " finished " << (isRead?"READ":"WRITE") << " for user " << userId << " at " << simTime() << endl;

        // Clean up original request and the service event message
        delete orig; // original request received from user
        removeEvent(msg);
        delete msg; // serviceDone event

        if (isRead) {
            activeReaders--;
            if (activeReaders < 0) activeReaders = 0; // safety
        } else {
            writeActive = false;
        }
        
        // If now idle (no readers active, no write), accumulate busy time
        bool nowIdle = (activeReaders == 0 && !writeActive);
        if (nowIdle) {
            totalBusyTime += simTime() - lastStateChange;
            lastStateChange = simTime();
        }

        // Try to start next services in queue
        processQueue();

    } else {
        // Arrival from a user: push into FIFO queue
        EV_DEBUG << "Table " << tableId << " received request " << msg->getName() << " from user "
                 << (msg->hasPar("userId") ? msg->par("userId").longValue() : -1) << " at " << simTime() << endl;

        requestQueue.push(msg);
        
        // Update queue length statistics and emit signal
        int qlen = requestQueue.size();
        if (qlen > maxQueueLength) maxQueueLength = qlen;
        totalQueueLength += qlen;
        queueLengthSamples++;
        emit(queueLengthSignal, qlen);

        // Try to start service if possible
        processQueue();
    }
}void Table::processQueue()
{
    // If a WRITE is in progress, everything is blocked.
    if (writeActive) {
        return;
    }

    // Process queue as long as possible
    while (!requestQueue.empty()) {
        cMessage *req = requestQueue.front();
        bool isReadRequest = (req->getKind() == 0); // 0 = READ

        if (isReadRequest) {
            // THIS IS A READ
            // Since writeActive is false (checked above), the read can proceed
            // EVEN IF there are already other active readers (activeReaders > 0).
            
            requestQueue.pop();           // Remove from queue
            startServiceForRequest(req);  // Start (increment activeReaders)
            
            // Continue loop! Other reads in queue can enter immediately.
        } 
        else {
            // THIS IS A WRITE
            // Write requires EXCLUSIVE access.
            // Must wait for activeReaders to reach 0.
            
            if (activeReaders == 0) {
                // Clear! Table is empty.
                requestQueue.pop();
                startServiceForRequest(req); // Will set writeActive = true
                
                // Now there's a writer, absolute stop.
                break; 
            } else {
                // Readers present. Write waits.
                // Being FCFS, write blocks everyone behind it.
                break;
            }
        }
    }
}

void Table::startServiceForRequest(cMessage *req)
{
    // Create a service completion event
    char buf[64];
    sprintf(buf, "serviceDone-%s", req->getName());
    cMessage *done = new cMessage(buf);
    // attach the original request so we can reply when the service completes
    done->setContextPointer((void*)req);

    // record this event for cleanup
    serviceEvents.push_back(done);

    // determine service time: prefer 'serviceTime' parameter on the request, else default 1.0
    double serviceTime = 1.0;
    if (req->hasPar("serviceTime")) serviceTime = req->par("serviceTime").doubleValue();
    
    // Calculate wait time in queue
    if (req->hasPar("arrivalTime")) {
        double arrTime = req->par("arrivalTime").doubleValue();
        double waitTime = simTime().dbl() - arrTime;
        totalWaitingTime += waitTime;
        emit(waitingTimeSignal, waitTime);
    }

    // update state before scheduling
    bool isRead = (req->getKind() == 0);
    
    // Track busy time: if was idle (0 readers, no write), now becomes busy
    bool wasBusy = (activeReaders > 0 || writeActive);
    
    if (isRead) {
        activeReaders++;
    } else {
        writeActive = true;
    }
    
    // If it was idle and now becomes busy, mark start of busy period
    if (!wasBusy) {
        lastStateChange = simTime();
    }

    scheduleAt(simTime() + serviceTime, done);

    EV_DEBUG << "Table " << tableId << " started " << (isRead?"READ":"WRITE") << " for user "
             << (req->hasPar("userId") ? req->par("userId").longValue() : -1) << " at " << simTime() << ", serviceTime=" << serviceTime << endl;
}

void Table::removeEvent(cMessage *evt)
{
    auto it = std::find(serviceEvents.begin(), serviceEvents.end(), evt);
    if (it != serviceEvents.end()) serviceEvents.erase(it);
}

void Table::finish()
{
    // Emit final statistics signals (course-standard method)
    emit(throughputSignal, totalServed);
    
    // Queue statistics
    if (queueLengthSamples > 0) {
        emit(queueLengthSignal, (int)(totalQueueLength / queueLengthSamples));
    }
    
    // Calculate and emit utilization
    simtime_t busyTime = totalBusyTime;
    if (activeReaders > 0 || writeActive) {
        busyTime += simTime() - lastStateChange;
    }
    double simDuration = simTime().dbl();
    if (simDuration > 0) {
        double util = busyTime.dbl() / simDuration;
        emit(utilizationSignal, util);
        recordScalar("table.utilization", util);
    }
    
    // Record some scalars for compatibility
    recordScalar("table.totalServed", totalServed);
    recordScalar("table.totalReads", totalReads);
    recordScalar("table.totalWrites", totalWrites);
    recordScalar("table.maxQueueLength", maxQueueLength);
    if (totalServed > 0) {
        recordScalar("table.avgWaitingTime", totalWaitingTime / totalServed);
    }
}
