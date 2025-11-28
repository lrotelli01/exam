package progetto;

network DatabaseNetwork
{
    parameters:
        int numUsers = default(10);   // N
        int numTables = default(5);   // M

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
        // Full mesh of gates: each user has tableOut[numTables] and tableIn[numTables]
        // each table has userIn[numUsers] and userOut[numUsers]
        for i=0..numUsers-1 for j=0..numTables-1 {
            user[i].tableOut[j] --> table[j].userIn[i];
            table[j].userOut[i] --> user[i].tableIn[j];
        }
}
