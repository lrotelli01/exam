package progetto;

network DatabaseNetwork
{
    parameters:
        // Calibrazione: 60 utenti e 20 tabelle per avere un carico medio sensato
        int numUsers = default(60); 
        int numTables = default(20);

    submodules:
        user[numUsers]: User {
            parameters:
                userId = index;
                // CORREZIONE: Usa 'parent.numTables' per prendere il valore dalla rete
                numTables = parent.numTables;
            gates:
                tableOut[parent.numTables];
                tableIn[parent.numTables];
        }

        table[numTables]: Table {
            parameters:
                tableId = index;
            gates:
                userIn[parent.numUsers];
                userOut[parent.numUsers];
        }

    connections allowunconnected:
        for i=0..numUsers-1, for j=0..numTables-1 {
            user[i].tableOut[j] --> table[j].userIn[i];
            table[j].userOut[i] --> user[i].tableIn[j];
        }
}