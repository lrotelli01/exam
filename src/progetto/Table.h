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

    // Statistics
    long totalServed; // total accesses served by this table
    long totalReads;
    long totalWrites;
    simtime_t busyTimeStart; // optional to measure utilization

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
