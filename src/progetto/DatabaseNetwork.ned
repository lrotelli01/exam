package progetto;

network DatabaseNetwork
{
    parameters:
        int numUsers = default(10);
        int numTables = default(5);

    submodules:
        user[numUsers]: User {
            parameters:
                userId = index;
                numTables = numTables;
        }

        table[numTables]: Table {
            parameters:
                tableId = index;
        }

    connections allowunconnected:
    for i=0..numUsers-1, for j=0..numTables-1 {
        user[i].tableOut[j] --> table[j].userIn[i];
        table[j].userOut[i] --> user[i].tableIn[j];
    }
}