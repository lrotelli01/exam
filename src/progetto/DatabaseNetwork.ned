//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Lesser General Public License as published by
// the Free Software Foundation, either version 3 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Lesser General Public License for more details.
//
// You should have received a copy of the GNU Lesser General Public License
// along with this program.  If not, see http://www.gnu.org/licenses/.
//

package exam.progetto;

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
        for i=0..numUsers-1 for j=0..numTables-1 {
            user[i].tableOut[j] --> table[j].userIn[i];
            table[j].userOut[i] --> user[i].tableIn[j];
        }
}