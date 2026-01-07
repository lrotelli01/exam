package progetto;

simple Table
{
    parameters:
        int tableId;    // Table ID

    gates:
        input userIn[];    // receives requests from all users
        output userOut[];  // sends responses to all users
        
    @signal[queueLength](type="int");           // Queue length over time
    @signal[waitingTime](type="double");        // Wait time per request
    @signal[throughput](type="int");            // Throughput (completed accesses)
    @signal[utilization](type="double");        // Table utilization
    
    @statistic[queueLength](source="queueLength"; record=mean,max,vector; title="Queue Length");
    @statistic[waitingTime](source="waitingTime"; record=mean,max,min,vector; title="Waiting Time");
    @statistic[throughput](source="throughput"; record=last; title="Total Served");
    @statistic[utilization](source="utilization"; record=last; title="Utilization");
}
