#ifndef __PROGETTO_USER_H_
#define __PROGETTO_USER_H_

#include <omnetpp.h>
#include <queue>

using namespace omnetpp;

// Struttura per rappresentare un'operazione sul database
struct DatabaseOperation {
    int tableId;           // ID della tabella da accedere
    bool isRead;           // true = lettura, false = scrittura
    double arrivalTime;    // Tempo di arrivo della richiesta
    double startTime;      // Tempo di inizio effettivo dell'operazione
};

class User : public cSimpleModule {
private:
    // Parametri della simulazione
    int userId;
    double lambda;                      // Rate di accesso (1/T)
    double readProbability;             // Probabilità di lettura (p)
    int numTables;                      // Numero di tabelle (M)
    std::string tableDistribution;      // "uniform" o "lognormal"
    double serviceTime;                 // Durata fissa operazione (S)
    
    // Variabili per statistiche
    long totalAccesses;                 // Totale operazioni completate
    long totalReads;                    // Totale operazioni di lettura
    long totalWrites;                   // Totale operazioni di scrittura
    double totalWaitTime;               // Tempo totale di attesa
    
    // Messaggi
    cMessage *accessTimer;              // Timer per il prossimo accesso
    
    // Statistiche di raccolta
    cOutVector readAccessVector;        // Numero di letture nel tempo
    cOutVector writeAccessVector;       // Numero di scritture nel tempo
    cOutVector waitTimeVector;          // Tempo di attesa per ogni operazione
    cOutVector accessIntervalVector;    // Intervallo tra accessi consecutivi
    
protected:
    virtual void initialize() override;
    virtual void handleMessage(cMessage *msg) override;
    virtual void finish() override;
    
private:
    // Metodi helper
    void scheduleNextAccess();
    int selectTableId();                // Seleziona ID tabella secondo la distribuzione
    int selectTableUniform();           // Distribuizione uniforme
    int selectTableLognormal();         // Distribuzione lognormale
    bool isReadOperation();             // Decide se è lettura (probabilità p)
    void sendAccessRequest(int tableId, bool isRead);
    void processTableResponse(cMessage *msg);
    double getExponentialDelay();       // Genera variabile esponenziale
};

#endif
