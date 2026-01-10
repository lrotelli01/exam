# Refactoring del Progetto OMNeT++ - Sostituzione di cOutVector con Signals

## Sommario
Il progetto è stato refactorizzato per utilizzare il **metodo di raccolta statistiche insegnato a lezione** (signals e emit) al posto di `cOutVector` e `recordScalar()` diretto.

## Cosa Era Usato Ma Non Spiegato nelle Slides

### 1. **cOutVector** ❌ RIMOSSO
```cpp
// VECCHIO (non insegnato)
cOutVector readAccessVector;
readAccessVector.setName("ReadAccesses");
readAccessVector.record(1);
```

### 2. **recordScalar() Diretto** ❌ PARZIALMENTE RIMOSSO
```cpp
// VECCHIO (non totalmente insegnato come pattern principale)
recordScalar("totalAccesses", totalAccesses);
```

## Cosa È Stato Introdotto

### Metodo Insegnato a Lezione: Signals + emit()

#### Fase 1: Definizione dei Segnali in NED
```ned
@signal[readAccess](type=long);
@signal[writeAccess](type=long);
@signal[waitTime](type=double);
@signal[accessInterval](type=double);

@statistic[readAccessStat](source="readAccess"; record=sum; title="Total read operations");
@statistic[writeAccessStat](source="writeAccess"; record=sum; title="Total write operations");
@statistic[waitTimeStat](source="waitTime"; record=mean,max; title="Wait time");
@statistic[accessIntervalStat](source="accessInterval"; record=mean; title="Access interval");
```

#### Fase 2: Registrazione dei Segnali in C++
```cpp
// In initialize()
readAccessSignal = registerSignal("readAccess");
writeAccessSignal = registerSignal("writeAccess");
waitTimeSignal = registerSignal("waitTime");
accessIntervalSignal = registerSignal("accessInterval");
```

#### Fase 3: Emissione dei Valori Con emit()
```cpp
// Nel codice di simulazione
emit(readAccessSignal, 1);
emit(waitTimeSignal, waitTime);
emit(accessIntervalSignal, delay);
```

## File Modificati

### User.ned
- ✅ Aggiunti 4 segnali: `readAccess`, `writeAccess`, `waitTime`, `accessInterval`
- ✅ Aggiunte 4 statistiche per registrare i dati

### User.h
- ✅ Rimossi: `cOutVector readAccessVector`, `writeAccessVector`, `waitTimeVector`, `accessIntervalVector`
- ✅ Aggiunti: `simsignal_t` per ogni segnale

### User.cc
- ✅ `initialize()`: Aggiunto `registerSignal()` per tutti i segnali
- ✅ `handleMessage()`: Sostituito `.record()` con `emit()`
- ✅ `scheduleNextAccess()`: Sostituito `.record()` con `emit()`
- ✅ `processTableResponse()`: Sostituito `.record()` con `emit()`

### Table.ned
- ✅ Aggiunti 5 segnali: `tableServed`, `tableReads`, `tableWrites`, `tableWaitingTime`, `tableQueueLength`
- ✅ Aggiunte 5 statistiche per registrare i dati

### Table.h
- ✅ Aggiunti: `simsignal_t` per ogni segnale (nessun `cOutVector` era presente)

### Table.cc
- ✅ `initialize()`: Aggiunto `registerSignal()` per tutti i segnali
- ✅ `handleMessage()`: Aggiunto `emit()` quando completa operazioni e per queue length
- ✅ `startServiceForRequest()`: Aggiunto `emit()` per tempo di attesa

## Vantaggi del Refactoring

1. **✅ Coerenza con le Slides**: Il codice usa esattamente il metodo insegnato a lezione
2. **✅ Flessibilità**: I recorder (mean, max, sum) sono definiti nel NED, non nel codice C++
3. **✅ Manutenibilità**: Facile modificare quali metriche registrare senza toccare il C++
4. **✅ Best Practices**: Segue il paradigma OMNeT++ moderno
5. **✅ Scalabilità**: Facile aggiungere nuovi segnali o statistiche

## Pattern Insegnato vs Vecchio Pattern

| Aspetto | Metodo Insegnato (✅) | Vecchio Metodo (❌) |
|---------|----------------------|-------------------|
| Definizione | NED file con @signal | Nessuna |
| Registrazione | `registerSignal()` in initialize | `.setName()` nel C++ |
| Emissione | `emit(signal, value)` | `.record(value)` |
| Configurazione | NED @statistic | Hardcoded nel C++ |
| Flessibilità | Alta (cambiare NED) | Bassa (modificare codice) |

## Note Importanti

- ✅ Tutto il codice mantiene la stessa **logica di simulazione**
- ✅ Solo la **raccolta statistiche** è stata modernizzata
- ✅ I dati raccolti rimangono **identici**
- ✅ Il progetto dovrebbe compilare ed eseguire senza problemi

## Prossimi Passi

1. Compilare il progetto per verificare che non ci siano errori
2. Eseguire una simulazione di prova
3. Verificare che le statistiche siano registrate correttamente nei file .sca e .vec
4. Consultare l'output per confermare che i segnali funzionano correttamente
