import json
from datetime import datetime

# Funzione per rimuovere gli attributi dagli oggetti JSON
def rimuovi_attributi(json_data, attributi_da_rimuovere):
    for oggetto in json_data:
        for attributo in attributi_da_rimuovere:
            oggetto.pop(attributo, None)  # Rimuovi l'attributo se presente
    return json_data

# Percorso del file JSON da leggere
percorso_file_input = './Databaseinaturalis/inaturalistOsservationsJson.txt'
# Percorso del file JSON in cui salvare i risultati

# Converti la data in una stringa
data_stringa = datetime.now().strftime('%Y_%m_%d_%H_%M_%S')
percorso_file_output = './Databaseinaturalis/inaturalistOsservationsJson'+data_stringa+'.json'

# Attributi da rimuovere dagli oggetti JSON
attributi_da_rimuovere = ['user_id', 'user_login','updated_at','quality_grade','license','sound_url','num_identification_agreements',
                          'num_identification_disagreements','captive_cultivated','oauth_application_id','positional_accuracy',
                          'private_place_guess','private_latitude','private_longitude','public_positional_accuracy','positioning_device','positioning_method',
                          'geoprivacy','taxon_geoprivacy','coordinates_obscured']

# Leggi il file JSON
with open(percorso_file_input) as file_input:
    json_data = json.load(file_input)

# Rimuovi gli attributi dagli oggetti JSON
json_data_modificato = rimuovi_attributi(json_data, attributi_da_rimuovere)

# Salva i risultati nel nuovo file JSON
with open(percorso_file_output, 'w') as file_output:
    json.dump(json_data_modificato, file_output)

