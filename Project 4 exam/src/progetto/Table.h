#ifndef __PROGETTO_TABLE_H_
#define __PROGETTO_TABLE_H_

#include <omnetpp.h>
#include <queue>
#include <vector>

using namespace omnetpp;

class Table : public cSimpleModule {
private:
    int tableId;
    int numUsers; // optional, for validation

    // Queue of pending requests (messages received from users)
    std::queue<cMessage*> requestQueue;

    // Number of active readers currently being served
    int activeReaders;

    // Whether a write is currently being served
    bool writeActive;

    // Track scheduled service completion events so they can be canceled/cleaned up
    std::vector<cMessage*> serviceEvents;

    // Signals for statistics collection (course-standard method)
    simsignal_t queueLengthSignal;      // Queue length
    simsignal_t waitingTimeSignal;      // Wait time per request
    simsignal_t throughputSignal;       // Throughput
    simsignal_t utilizationSignal;      // Utilization
    
    // Queue statistics
    int maxQueueLength;
    double totalQueueLength;
    int queueLengthSamples;
    double totalWaitingTime;
    
    // Service statistics
    long totalServed;                   // Total requests served
    long totalReads;                    // Total read operations served
    long totalWrites;                   // Total write operations served
    simtime_t busyTimeStart;            // Start of busy period
    simtime_t totalBusyTime;            // Total busy time accumulated
    simtime_t lastStateChange;          // Last time state changed

protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;
    virtual void removeEvent(cMessage *evt);
    virtual void processQueue();
    virtual void startServiceForRequest(cMessage *req);

public:
    Table();
    virtual ~Table();
};

#endif // __PROGETTO_TABLE_H_
