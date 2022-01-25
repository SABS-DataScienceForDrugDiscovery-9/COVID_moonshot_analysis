
import re
import csv
import sqlite3
from pathlib import Path
from pprint import pprint

all_data_file = Path('/home/dtc-user/Documents/COVID_moonshot_analysis/COVID_moonshot_submissions/covid_submissions_all_info.csv')

class DatabaseFactory():
    def __init__(self, database_path: str):
        """
        Parameters
        ----------
        database_path: str
            Full path of existing SQLite database or one to be created automatically
        """

        # Store SQLite database path for reference
        self._database_path = database_path

        # Connect to and Create (if doesn't already exist) SQLite database
        self._conn = sqlite3.connect(database_path)

        # List of tables that need to be dropped to reset the SQLite database
        self._drop_order = ('assays', 'rdkit_descriptors', 'compounds')

    def get_conn(self):
        """
        get_conn returns a connection to the SQLite database self._database_path

        Returns
        -------
            SQLite connection object
        """
        return self._conn

    def drop_all(self):
        """
        drop_all drops all tables created by this class to reset the SQLite database
        """

        # Get connection to SQLite database
        conn = self.get_conn()

        # Drop all tables in dependency order
        for table_name in self._drop_order:
            conn.execute('DROP TABLE IF EXISTS ' + table_name)

    def create(self):
        """
        create - creates all tables required by this class in the SQLite database
        """

        # Get connection to SQLite database
        conn = self.get_conn()

        # Create a table to store all COVID Moonshot submissions
        conn.execute('''
            CREATE TABLE compounds
            (
                id VARCHAR(20) PRIMARY KEY,
                smiles VARCHAR(2000) not null UNIQUE,
                MW DECIMAL not null,
                NMR_std_ratio DECIMAL,
                assayed BOOLEAN
            )
            ''')

        # Create a table to store all COVID Moonshot compound submissions
        conn.execute('''
            CREATE TABLE assays
            (
                id VARCHAR(20) PRIMARY KEY,
                compound_id VARCHAR(20) not null,
                r_inhibition_at_20_uM DECIMAL,
                r_inhibition_at_50_uM DECIMAL,
                r_avg_IC50 DECIMAL,
                r_curve_IC50 DECIMAL,
                r_max_inhibition_reading DECIMAL,
                r_min_inhibition_reading DECIMAL,
                r_hill_slope DECIMAL,
                r_R2 DECIMAL,
                f_inhibition_at_20_uM DECIMAL,
                f_inhibition_at_50_uM DECIMAL,
                f_avg_IC50 DECIMAL,
                f_avg_pIC50 DECIMAL,
                f_curve_IC50 DECIMAL,
                f_max_inhibition_reading DECIMAL,
                f_min_inhibition_reading DECIMAL,
                f_hill_slope DECIMAL,
                f_R2 DECIMAL,
                relative_solubility_at_20_uM DECIMAL,
                relative_solubility_at_100_uM DECIMAL,
                trypsin_IC50 DECIMAL,

                FOREIGN KEY(compound_id) REFERENCES compound_id(compound_id) 
            )
            ''')

        conn.execute('''
            CREATE TABLE rdkit_descriptors
            (
                id VARCHAR(20) PRIMARY KEY,
                compound_id VARCHAR(20) not null,
                cLogP DECIMAL,
                HBD DECIMAL,
                HBA DECIMAL,
                TPSA DECIMAL,

                FOREIGN KEY(compound_id) REFERENCES compound_id(compound_id) 
            )
            ''')

    def show_tables(self):
        """
        show_tables - prints out the SQL used to built all the tables in our SQLite database
        """

        # Get a connection to our SQLite database
        conn = self.get_conn()

        # Generate a list of tables within our SQLite database

        # Execute an SQL statement to get a cursor object to iterate over the SQL statement results
        cur = conn.execute('''
            SELECT 
                name
            FROM 
                sqlite_master 
            WHERE 
                type ='table' AND 
                name NOT LIKE 'sqlite_%'
        ''')

        tables = []

        for row in cur.fetchall():
            tables.append(row[0])

        # Iterate over the tables in our SQLite database and fetch and print their SQL definitions
        for table in tables:
            cur = conn.execute('SELECT  sql  FROM  sqlite_master  WHERE name=\'' + table + '\'')

            row = cur.fetchone()

            if row is not None:
                print(table+'\n')

                print(row[0])
            else:
                print('Table ' + table + ' not found')
        

    def populate(self, all_data_file: Path):
        with open(all_data_file, 'r') as f:
            reader = csv.DictReader(f, delimiter=',')

            compound_data = []
            rdkit_descriptors = []
            assay_data = []
            for row in reader:
                compound_data.append((
                    row["CID"], row["SMILES"], row["MW"], row["NMR_std_ratio"], row["ASSAYED"]=="TRUE"))
                rdkit_descriptors.append((
                    row["CID"], row["SMILES"], row["cLogP"], row["HBD"], row["HBA"], row["TPSA"]))
                if (row["ASSAYED"] == "TRUE"):
                    assay_data.append((
                        row["CID"], row["SMILES"], row["r_inhibition_at_20_uM"], row["r_inhibition_at_50_uM"],
                        row["r_avg_IC50"], row["r_max_inhibition_reading"], row["r_min_inhibition_reading"],
                        row["r_hill_slope"], row["r_R2"], row["f_inhibition_at_20_uM"],
                        row["f_inhibition_at_50_uM"], row["f_avg_IC50"], row["f_avg_pIC50"],
                        row["f_curve_IC50"], row["f_max_inhibition_reading"],
                        row["f_min_inhibition_reading"], row["f_hill_slope"], row["f_R2"],
                        row["relative_solubility_at_20_uM"], row["relative_solubility_at_100_uM"],
                        row["trypsin_IC50"]))

        conn = self.get_conn()
        conn.executemany("""
        INSERT INTO compounds
            (id, smiles, MW, NMR_std_ratio, assayed)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (smiles) DO NOTHING;
        """, compound_data)

        conn.executemany("""
        INSERT INTO rdkit_descriptors
            (id, compound_id, cLogP, HBD, HBA, TPSA)
        VALUES (?,(SELECT compounds.id FROM compounds where compounds.smiles = ?),?,?,?,?)
        ON CONFlICT (id) DO NOTHING;
        """, rdkit_descriptors)

        conn.executemany("""
        INSERT INTO assays
            (id, compound_id, r_inhibition_at_20_uM, r_inhibition_at_50_uM,
            r_avg_IC50, r_max_inhibition_reading, r_min_inhibition_reading,
            r_hill_slope, r_R2, f_inhibition_at_20_uM,
            f_inhibition_at_50_uM, f_avg_IC50, f_avg_pIC50,
            f_curve_IC50, f_max_inhibition_reading,
            f_min_inhibition_reading, f_hill_slope, f_R2,
            relative_solubility_at_20_uM, relative_solubility_at_100_uM,
            trypsin_IC50)
        VALUES (?, (SELECT compounds.id FROM compounds where compounds.smiles = ?), ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?, ?,
            ?, ?,
            ?, ?, ?,
            ?, ?,
            ?)
        ON CONFLICT (id) DO NOTHING;
        """, assay_data)


def main():
    manager = DatabaseFactory(database_path='sabs_moonshot.db')
    manager.drop_all()
    manager.create()
    manager.show_tables()
    manager.populate(all_data_file=all_data_file)

    manager.get_conn().commit()

if __name__ == '__main__':
    main()