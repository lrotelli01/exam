package progetto;

simple User
{
    parameters:
        int userId;                    // User ID (0 to N-1)
        double lambda;                 // Poisson process rate (1/T) - accesses per second
        double readProbability;        // Probability of read operation (p)
        int numTables;                 // Total number of tables (M)
        string tableDistribution;      // "uniform" or "lognormal" to choose distribution
        double serviceTime @unit(s);   // Fixed operation duration (S seconds)
        double lognormalM = default(0.5);
        double lognormalS = default(1.0);
        
    gates:
        output tableOut[];             // Outputs to all tables
        input tableIn[];               // Inputs from tables
        
    @signal[waitTime](type="double");           // Signal for wait time
    @signal[readAccess](type="int");            // Signal for read accesses
    @signal[writeAccess](type="int");           // Signal for write accesses
    @signal[accessInterval](type="double");     // Signal for access interval
    
    @statistic[waitTime](source="waitTime"; record=mean,max,min,vector; title="Wait Time");
    @statistic[readAccess](source="readAccess"; record=count; title="Read Accesses");
    @statistic[writeAccess](source="writeAccess"; record=count; title="Write Accesses");
    @statistic[accessInterval](source="accessInterval"; record=mean,vector; title="Access Interval");
}
