#include "User.h"

Define_Module(User);

void User::initialize()
{
    // Read parameters
    userId = par("userId");
    lambda = par("lambda");
    readProbability = par("readProbability");
    numTables = par("numTables");
    tableDistribution = par("tableDistribution").stringValue();
    serviceTime = par("serviceTime");
    
    // Initialize variables
    totalAccesses = 0;
    totalReads = 0;
    totalWrites = 0;
    totalWaitTime = 0.0;
    
    // Register signals (course-standard method - signal mechanism)
    waitTimeSignal = registerSignal("waitTime");
    readAccessSignal = registerSignal("readAccess");
    writeAccessSignal = registerSignal("writeAccess");
    accessIntervalSignal = registerSignal("accessInterval");
    
    // Create first access event
    accessTimer = new cMessage("AccessTimer");
    scheduleNextAccess();
    
    EV_INFO << "User " << userId << " initialized with lambda=" << lambda 
            << ", readProb=" << readProbability 
            << ", numTables=" << numTables 
            << ", distribution=" << tableDistribution << endl;
}

void User::handleMessage(cMessage *msg)
{
    if (msg == accessTimer) {
        // Time for a new access
        
        // Select table according to specified distribution
        int tableId = selectTableId();
        
        // Decide if read or write operation
        bool isRead = isReadOperation();
        
        // Record operation type
        if (isRead) {
            totalReads++;
            emit(readAccessSignal, 1);
        } else {
            totalWrites++;
            emit(writeAccessSignal, 1);
        }
        
        totalAccesses++;
        
        EV_DEBUG << "User " << userId << " requested access to Table " << tableId 
                 << " (" << (isRead ? "READ" : "WRITE") << ") at time " << simTime() << endl;
        
        // Send request to table
        sendAccessRequest(tableId, isRead);
        
        // Schedule next access
        scheduleNextAccess();
        
    } else {
        // Response message from table
        processTableResponse(msg);
    }
}

void User::scheduleNextAccess()
{
    // Generate inter-arrival time according to exponential distribution
    double delay = getExponentialDelay();
    
    emit(accessIntervalSignal, delay);
    scheduleAt(simTime() + delay, accessTimer);
}

int User::selectTableId()
{
    if (tableDistribution == "uniform") {
        return selectTableUniform();
    } else if (tableDistribution == "lognormal") {
        return selectTableLognormal();
    } else {
        error("Unknown table distribution: %s", tableDistribution.c_str());
        return 0;
    }
}

int User::selectTableUniform()
{
    // Uniform distribution: each table has equal probability
    // Returns a value from 0 to numTables-1
    return intuniform(0, numTables - 1);
}

int User::selectTableLognormal()
{
    // Lognormal distribution
    // Parameters: m (mean of log) and s (std dev of log)
    
    double m = par("lognormalM");
    double s = par("lognormalS");
    // Generate variable with lognormal distribution
    // lognormal(m, s) where m is mean of natural logarithm
    double logNormalValue = lognormal(m, s);
    
    // Map lognormal value to interval [0, numTables-1]
    // Use modulo to ensure result is always in valid range
    int tableId = (int)(fmod(logNormalValue, numTables));
    if (tableId < 0) tableId = 0;
    if (tableId >= numTables) tableId = numTables - 1;
    
    return tableId;
}

bool User::isReadOperation()
{
    // Generate random number between 0 and 1
    // If less than readProbability, it's a read
    return uniform(0, 1) < readProbability;
}

void User::sendAccessRequest(int tableId, bool isRead)
{
    // Create new message for request
    cMessage *request = new cMessage();

    // Set message name for debugging
    if (isRead) {
        request->setName("ReadRequest");
        request->setKind(0);  // 0 = READ
    } else {
        request->setName("WriteRequest");
        request->setKind(1);  // 1 = WRITE
    }

    // Add request information as parameters
    cMsgPar *userIdPar = new cMsgPar("userId");
    userIdPar->setLongValue(userId);
    request->addPar(userIdPar);

    cMsgPar *arrivalTimePar = new cMsgPar("arrivalTime");
    arrivalTimePar->setDoubleValue(simTime().dbl());
    request->addPar(arrivalTimePar);

    cMsgPar *serviceTimePar = new cMsgPar("serviceTime");
    serviceTimePar->setDoubleValue(serviceTime);
    request->addPar(serviceTimePar);

    // Send message to appropriate table gate
    send(request, "tableOut", tableId);
}

void User::processTableResponse(cMessage *msg)
{
    // Response message from table
    double arrivalTime = msg->par("arrivalTime").doubleValue();
    double completionTime = simTime().dbl();
    double waitTime = completionTime - arrivalTime;

    totalWaitTime += waitTime;
    emit(waitTimeSignal, waitTime);

    bool isRead = (msg->getKind() == 0);  // 0 = READ, 1 = WRITE

    EV_DEBUG << "User " << userId << " received response for "
             << (isRead ? "READ" : "WRITE") << " at time " << simTime()
             << ", wait time: " << waitTime << "s" << endl;

    // Delete message
    delete msg;
}

double User::getExponentialDelay()
{
    // Generate exponential inter-arrival with rate lambda
    // If lambda = 1/T, then generated value is distributed as Exp(lambda)
    return exponential(1.0 / lambda);
}

void User::finish()
{
    // Final statistics
    double avgWaitTime = (totalAccesses > 0) ? (totalWaitTime / totalAccesses) : 0.0;
    double accessesPerSecond = totalAccesses / simTime().dbl();
    
    EV_INFO << endl << "=== Statistics for User " << userId << " ===" << endl;
    EV_INFO << "Total accesses: " << totalAccesses << endl;
    EV_INFO << "Total reads: " << totalReads << endl;
    EV_INFO << "Total writes: " << totalWrites << endl;
    EV_INFO << "Average wait time: " << avgWaitTime << " seconds" << endl;
    EV_INFO << "Accesses per second: " << accessesPerSecond << endl;
    EV_INFO << "========================================" << endl;
    
    // Record statistics
    recordScalar("totalAccesses", totalAccesses);
    recordScalar("totalReads", totalReads);
    recordScalar("totalWrites", totalWrites);
    recordScalar("averageWaitTime", avgWaitTime);
    recordScalar("accessesPerSecond", accessesPerSecond);
}
