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

        // Try to start next services in queue
        processQueue();

    } else {
        // Arrival from a user: push into FIFO queue
        EV_DEBUG << "Table " << tableId << " received request " << msg->getName() << " from user "
                 << (msg->hasPar("userId") ? msg->par("userId").longValue() : -1) << " at " << simTime() << endl;

        requestQueue.push(msg);

        // Try to start service if possible
        processQueue();
    }
}void Table::processQueue()
{
    // Se c'è una SCRITTURA in corso, tutto è bloccato.
    if (writeActive) {
        return;
    }

    // Processiamo la coda finché possibile
    while (!requestQueue.empty()) {
        cMessage *req = requestQueue.front();
        bool isReadRequest = (req->getKind() == 0); // 0 = READ

        if (isReadRequest) {
            // È UNA LETTURA
            // Poiché writeActive è false (controllato sopra), la lettura può entrare
            // ANCHE SE ci sono già altri lettori attivi (activeReaders > 0).
            
            requestQueue.pop();           // Togli dalla coda
            startServiceForRequest(req);  // Avvia (incrementa activeReaders)
            
            // Continua il ciclo! Altre letture in coda potrebbero entrare subito.
        } 
        else {
            // È UNA SCRITTURA
            // La scrittura richiede accesso ESCLUSIVO.
            // Deve aspettare che activeReaders scenda a 0.
            
            if (activeReaders == 0) {
                // Via libera! Tabella vuota.
                requestQueue.pop();
                startServiceForRequest(req); // Imposterà writeActive = true
                
                // Ora c'è uno scrittore, stop assoluto.
                break; 
            } else {
                // Ci sono lettori. La scrittura aspetta.
                // Essendo FCFS, la scrittura blocca chiunque ci sia dietro di lei.
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

    // update state before scheduling
    bool isRead = (req->getKind() == 0);
    if (isRead) {
        activeReaders++;
    } else {
        writeActive = true;
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
    // record scalars
    recordScalar("table.totalServed", totalServed);
    recordScalar("table.totalReads", totalReads);
    recordScalar("table.totalWrites", totalWrites);
}
