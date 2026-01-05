# Statistiche Implementate

## ✅ Requisito Principale SODDISFATTO
**"Evaluate at least the number of served accesses per unit time"**
- ✅ `accessesPerSecond` (User) - Accessi serviti per unità di tempo per utente
- ✅ `table.throughput` (Table) - Accessi serviti per secondo per tabella
- ✅ Aggregazione globale nello script `analyze_results.py`

## 📊 Statistiche per Utente (User.cc)

### Metriche Fondamentali
1. **totalAccesses** - Numero totale di accessi richiesti
2. **totalReads** - Numero di operazioni di lettura
3. **totalWrites** - Numero di operazioni di scrittura
4. **averageWaitTime** - Tempo medio di attesa (dalla richiesta alla risposta)
5. **accessesPerSecond** - **[RICHIESTO]** Throughput: accessi completati/secondo

### Vector Outputs (serie temporali)
- **ReadAccesses** - Traccia ogni accesso in lettura
- **WriteAccesses** - Traccia ogni accesso in scrittura
- **WaitTime** - Tempo di attesa per ogni richiesta
- **AccessInterval** - Intervallo tra accessi consecutivi

## 📊 Statistiche per Tabella (Table.cc) - APPENA AGGIUNTE

### Metriche di Throughput
1. **table.totalServed** - Totale accessi serviti dalla tabella
2. **table.totalReads** - Totale letture servite
3. **table.totalWrites** - Totale scritture servite
4. **table.throughput** - **[RICHIESTO]** Accessi/secondo per tabella

### Metriche di Performance
5. **table.avgWaitingTime** - Tempo medio di attesa in coda
6. **table.utilization** - Frazione di tempo con tabella occupata (0-1)

### Metriche di Congestione
7. **table.maxQueueLength** - Lunghezza massima coda raggiunta
8. **table.avgQueueLength** - Lunghezza media della coda

## 📈 Metriche Utili per l'Analisi

### Impatto di N (numero utenti)
- **throughput vs N**: Verifica scalabilità
- **avgWaitTime vs N**: Identifica saturazione
- **table.utilization vs N**: Mostra carico sistema
- **avgQueueLength vs N**: Indica congestione

### Impatto di p (probabilità lettura)
- **totalReads/totalWrites ratio**: Verifica calibrazione
- **avgWaitTime per Read vs Write**: Confronta priorità
- **table.utilization**: Write monopolizzano più tempo

### Confronto Distribuzioni
- **Uniform vs Lognormal**:
  - Distribuzione carico tra tabelle
  - table.throughput per singola tabella
  - table.maxQueueLength identifica hotspot

## 🔧 Come Ricompilare

```bash
cd /home/luca/Scaricati/omnetpp-6.2.0-linux-x86_64/omnetpp-6.2.0
source setenv
cd exam
make clean
make MODE=release
```

Se `make` non funziona, usa lo script `run` che rileverà automaticamente i file modificati:

```bash
cd simulations
./run -u Cmdenv -c Uniform
```

## 📊 Analisi dei Risultati

Lo script `analyze_results.py` è già configurato per leggere:
- `totalAccesses`, `totalReads`, `totalWrites`
- `averageWaitTime`
- `accessesPerSecond` (throughput per utente)

**Aggiungere al `analyze_results.py` per le nuove statistiche:**

```python
# Statistiche tabelle
table_throughput = {}
table_utilization = {}
table_queue_length = {}

for scalar in scalars:
    if scalar.startswith('Table['):
        table_id = scalar.split('[')[1].split(']')[0]
        if 'table.throughput' in scalar:
            table_throughput[table_id] = value
        elif 'table.utilization' in scalar:
            table_utilization[table_id] = value
        elif 'table.avgQueueLength' in scalar:
            table_queue_length[table_id] = value
```

## 🎯 Validazione Requisiti

| Requisito | Statistica | Status |
|-----------|-----------|---------|
| "number of served accesses per unit time" | `accessesPerSecond` (User)<br>`table.throughput` (Table) | ✅ |
| Variazione con N | Sweep N=[50,100,200] | ✅ |
| Variazione con p | Sweep p=[0.5,0.8] | ✅ |
| Uniform distribution | Config Uniform | ✅ |
| Lognormal distribution | Config Lognormal | ✅ |
| Confronto prestazioni | Multipli repeat=5 | ✅ |

## 📌 Statistiche Aggiuntive Consigliate

Per una presentazione completa (max 10 slide), includere:

1. **Slide 1-2**: Problema e modello
2. **Slide 3-4**: Throughput globale vs N e p
3. **Slide 5**: Tempi di attesa vs N
4. **Slide 6**: Utilization sistema vs N
5. **Slide 7**: Confronto Uniform vs Lognormal
6. **Slide 8**: Distribuzione carico tra tabelle (hotspot)
7. **Slide 9**: Validazione (read/write ratio)
8. **Slide 10**: Conclusioni e insights
