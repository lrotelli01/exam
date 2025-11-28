#include "User.h"

Define_Module(User);

void User::initialize()
{
    // Lettura dei parametri
    userId = par("userId");
    lambda = par("lambda");
    readProbability = par("readProbability");
    numTables = par("numTables");
    tableDistribution = par("tableDistribution").stringValue();
    serviceTime = par("serviceTime");
    
    // Inizializzazione variabili
    totalAccesses = 0;
    totalReads = 0;
    totalWrites = 0;
    totalWaitTime = 0.0;
    
    // Registrazione delle statistiche (cOutVector)
    readAccessVector.setName("ReadAccesses");
    writeAccessVector.setName("WriteAccesses");
    waitTimeVector.setName("WaitTime");
    accessIntervalVector.setName("AccessInterval");
    
    // Creazione del primo evento di accesso
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
        // È il momento di effettuare un nuovo accesso
        
        // Seleziona la tabella secondo la distribuzione specificata
        int tableId = selectTableId();
        
        // Decidi se è lettura o scrittura
        bool isRead = isReadOperation();
        
        // Registra il tipo di operazione
        if (isRead) {
            totalReads++;
            readAccessVector.record(1);
        } else {
            totalWrites++;
            writeAccessVector.record(1);
        }
        
        totalAccesses++;
        
        EV_DEBUG << "User " << userId << " requested access to Table " << tableId 
                 << " (" << (isRead ? "READ" : "WRITE") << ") at time " << simTime() << endl;
        
        // Invia richiesta alla tabella
        sendAccessRequest(tableId, isRead);
        
        // Programma il prossimo accesso
        scheduleNextAccess();
        
    } else {
        // Messaggio di risposta dalla tabella
        processTableResponse(msg);
    }
}

void User::scheduleNextAccess()
{
    // Genera il tempo di inter-arrivo secondo una distribuzione esponenziale
    double delay = getExponentialDelay();
    
    accessIntervalVector.record(delay);
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
    // Distribuzione uniforme: ogni tabella ha uguale probabilità
    // Ritorna un valore da 0 a numTables-1
    return intuniform(0, numTables - 1);
}

int User::selectTableLognormal()
{
    // Distribuzione lognormale
    // Parametri della lognormale: m (media del log) e s (dev std del log)
    // Calibra questi valori a seconda del tuo scenario
    double m = par("lognormalM");
    double s = par("lognormalS");
    // Genera una variabile con distribuzione lognormale
    // lognormal(m, s) dove m è la media del logaritmo naturale
    double logNormalValue = lognormal(m, s);
    
    // Mappa il valore lognormale all'intervallo [0, numTables-1]
    // Usa il modulo per garantire che il risultato sia sempre nell'intervallo valido
    int tableId = (int)(fmod(logNormalValue, numTables));
    if (tableId < 0) tableId = 0;
    if (tableId >= numTables) tableId = numTables - 1;
    
    return tableId;
}

bool User::isReadOperation()
{
    // Genera un numero casuale tra 0 e 1
    // Se è minore di readProbability, è una lettura
    return uniform(0, 1) < readProbability;
}

void User::sendAccessRequest(int tableId, bool isRead)
{
    // Crea un nuovo messaggio per la richiesta
    cMessage *request = new cMessage();
    
    // Imposta il nome del messaggio per debugging
    if (isRead) {
        request->setName("ReadRequest");
        request->setKind(0);  // 0 = READ
    } else {
        request->setName("WriteRequest");
        request->setKind(1);  // 1 = WRITE
    }
    
    // Aggiungi informazioni sulla richiesta come parametri
    // Puoi usare cMessage::addPar() o una struttura dati personalizzata
    cMsgPar *userIdPar = new cMsgPar("userId");
    userIdPar->setLongValue(userId);
    request->addPar(userIdPar);
    
    cMsgPar *arrivalTimePar = new cMsgPar("arrivalTime");
    arrivalTimePar->setDoubleValue(simTime().dbl());
    request->addPar(arrivalTimePar);
    
    cMsgPar *serviceTimePar = new cMsgPar("serviceTime");
    serviceTimePar->setDoubleValue(serviceTime);
    request->addPar(serviceTimePar);
    
    // Invia il messaggio al gate della tabella appropriata
    send(request, "tableOut", tableId);
}

void User::processTableResponse(cMessage *msg)
{
    // Messaggio di risposta dalla tabella
    double arrivalTime = msg->par("arrivalTime").doubleValue();
    double completionTime = simTime().dbl();
    double waitTime = completionTime - arrivalTime;
    
    totalWaitTime += waitTime;
    waitTimeVector.record(waitTime);
    
    bool isRead = (msg->getKind() == 0);  // 0 = READ, 1 = WRITE
    
    EV_DEBUG << "User " << userId << " received response for " 
             << (isRead ? "READ" : "WRITE") << " at time " << simTime() 
             << ", wait time: " << waitTime << "s" << endl;
    
    // Elimina il messaggio
    delete msg;
}

double User::getExponentialDelay()
{
    // Genera un inter-arrivo esponenziale con rate lambda
    // Se lambda = 1/T, allora il valore generato è distribuito come Exp(lambda)
    return exponential(1.0 / lambda);
}

void User::finish()
{
    // Statistiche finali
    double avgWaitTime = (totalAccesses > 0) ? (totalWaitTime / totalAccesses) : 0.0;
    double accessesPerSecond = totalAccesses / simTime().dbl();
    
    EV_INFO << endl << "=== Statistics for User " << userId << " ===" << endl;
    EV_INFO << "Total accesses: " << totalAccesses << endl;
    EV_INFO << "Total reads: " << totalReads << endl;
    EV_INFO << "Total writes: " << totalWrites << endl;
    EV_INFO << "Average wait time: " << avgWaitTime << " seconds" << endl;
    EV_INFO << "Accesses per second: " << accessesPerSecond << endl;
    EV_INFO << "========================================" << endl;
    
    // Registra le statistiche
    recordScalar("totalAccesses", totalAccesses);
    recordScalar("totalReads", totalReads);
    recordScalar("totalWrites", totalWrites);
    recordScalar("averageWaitTime", avgWaitTime);
    recordScalar("accessesPerSecond", accessesPerSecond);
}
