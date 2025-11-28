package progetto;

simple User
{
    parameters:
        int userId;                    // ID dell'utente (0 a N-1)
        double lambda;                 // Rate del processo di Poisson (1/T) - accessi al secondo
        double readProbability;        // Probabilità di operazione di lettura (p)
        int numTables;                 // Numero totale di tabelle (M)
        string tableDistribution;      // "uniform" o "lognormal" per scegliere la distribuzione di m
        double serviceTime;            // Durata fissa dell'operazione (S secondi)
        double lognormalM = default(0.5);
        double lognormalS = default(1.0);
        
    gates:
        output tableOut[];             // Uscite verso tutte le tabelle
        input tableIn[];               // Ingressi dalle tabelle
}
