package progetto;

simple User
{
    parameters:
        int userId;
        double lambda;
        double readProbability;
        int numTables;
        string tableDistribution;
        double serviceTime @unit(s);
        double lognormalM = default(0.5);
        double lognormalS = default(1.0);
        @signal[waitTime](type="double");
        @signal[readAccess](type="int");
        @signal[writeAccess](type="int");
        @signal[accessInterval](type="double");
        @statistic[waitTime](source="waitTime"; record=mean,max,min,vector);
        @statistic[readAccess](source="readAccess"; record=count);
        @statistic[writeAccess](source="writeAccess"; record=count);
        @statistic[accessInterval](source="accessInterval"; record=mean,vector);

    gates:
        output tableOut[];
        input tableIn[];
}
