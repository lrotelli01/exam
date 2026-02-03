#ifndef __PROGETTO_USER_H_
#define __PROGETTO_USER_H_

#include <omnetpp.h>
#include <queue>

using namespace omnetpp;

// Structure representing a database operation
struct DatabaseOperation {
    int tableId;           // ID of the table to access
    bool isRead;           // true = read, false = write
    double arrivalTime;    // Time when request arrived
    double startTime;      // Time when operation actually started
};

class User : public cSimpleModule {
private:
    // Simulation parameters
    int userId;
    double lambda;                      // Access rate (1/T)
    double readProbability;             // Read probability (p)
    int numTables;                      // Number of tables (M)
    std::string tableDistribution;      // "uniform" or "lognormal"
    double serviceTime;                 // Fixed operation duration (S)
    
    // Statistics variables
    long totalAccesses;                 // Total completed operations
    long totalReads;                    // Total read operations
    long totalWrites;                   // Total write operations
    double totalWaitTime;               // Total waiting time
    
    // Messages
    cMessage *accessTimer;              // Timer for next access
    
    // Signals for statistics collection (course-standard method)
    simsignal_t waitTimeSignal;         // Signal for wait time
    simsignal_t readAccessSignal;       // Signal for read accesses
    simsignal_t writeAccessSignal;      // Signal for write accesses
    simsignal_t accessIntervalSignal;   // Signal for access interval
    
protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;
    
private:
    // Helper methods
    void scheduleNextAccess();
    int selectTableId();                // Select table ID according to distribution
    int selectTableUniform();           // Uniform distribution
    int selectTableLognormal();         // Lognormal distribution
    bool isReadOperation();             // Decide if read operation (probability p)
    void sendAccessRequest(int tableId, bool isRead);
    void processTableResponse(cMessage *msg);
    double getExponentialDelay();       // Generate exponential random variable
};

#endif
