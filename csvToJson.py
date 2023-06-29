import csv
import json

def convert_csv_to_json(csv_file_path, json_file_path):
    # Apri il file CSV in modalità di lettura
    with open(csv_file_path, 'r') as csv_file:
        # Leggi il contenuto del file CSV
        csv_data = csv.DictReader(csv_file)
        
        # Crea una lista di dizionari dal contenuto del file CSV
        data_list = list(csv_data)
        
    # Apri il file JSON in modalità di scrittura
    with open(json_file_path, 'w') as json_file:
        # Scrivi i dati nel file JSON
        json.dump(data_list, json_file, indent=4)

if __name__=="__main__":
	convert_csv_to_json("./Databaseinaturalis/invaturalisOsservations.csv","./Databaseinaturalis/inaturalistOsservationsJson.txt")
