package progetto;

simple Table
{
    parameters:
        int tableId;
        @signal[queueLength](type="int");
        @signal[waitingTime](type="double");
        @signal[throughput](type="int");
        @signal[utilization](type="double");
        @statistic[queueLength](source="queueLength"; record=mean,max,vector);
        @statistic[waitingTime](source="waitingTime"; record=mean,max,min,vector);
        @statistic[throughput](source="throughput"; record=last);
        @statistic[utilization](source="utilization"; record=last);

    gates:
        input userIn[];
        output userOut[];
}

