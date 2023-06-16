import json

from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
import re
from datetime import datetime

app = Flask(__name__)


# Configurazione MongoDB
# client = MongoClient('mongodb://localhost:27017/')
# db = client['mydatabase']
# collection = db['mycollection']

@app.route('/insertuser', methods=['POST'])
def insert_user():
    username = request.form['username']
    email = request.form['email']
    password = request.form['password']

    # Verifica che l'email abbia il formato corretto
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return "Email non valida!"

    # Logica per inserire l'utente nel database o fare altre operazioni

    return redirect(url_for('register'))


@app.route('/')
def index():
    client = MongoClient("mongodb://localhost:27017/")
    db_name = "mongoDBproject"
    db = client[db_name]
    # Ottenere 30 documenti casuali dalla collezione
    pipeline = [
        {'$sample': {'size': 8}}
    ]

    collezioni = db.list_collection_names()
    collezioni_da_evitare = ['utenti', 'stati', 'regioni', 'citta']
    collezioni_filtrate = [collezione for collezione in collezioni if collezione not in collezioni_da_evitare]

    random_documents = {}
    for collection in collezioni_filtrate:
        print(collection)
        random_documents[collection] = list(db.get_collection(collection).aggregate(pipeline))

    print(random_documents)

    return render_template('index.html', documents=random_documents)


@app.route('/crea_db')
def crea_db():
    # Connessione e Creazione del database
    client = MongoClient("mongodb://localhost:27017/")
    db_name = "mongoDBproject"
    db = client[db_name]
    # cancello e poi ricreo
    client.drop_database(db_name)

    # creo collezione utenti e admin username e passwd obbligatori
    schema_utenti = {
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["username", "password"],  # Campi obbligatori
                "properties": {
                    "username": {
                        "bsonType": "string",  # Tipo di dato per campo1
                    },
                    "password": {
                        "bsonType": "string",  # Tipo di dato per campo2
                    }
                }
            }
        }
    }
    utenti_collection = db.create_collection("utenti", **schema_utenti)
    utenti_collection.create_index("username", unique=True)
    utenti_collection.insert_one({"username": "admin", "password": "admin", "isAdmin": True})

    # creo collezioni stato (solo nome), regione (solo nome), città (nome + latitudine longitudine facoltativi)
    schema_stati = {
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["nome"],  # Campi obbligatori
                "properties": {
                    "nome": {
                        "bsonType": "string",  # Tipo di dato per campo1
                    }
                }
            }
        }
    }
    stati_collection = db.create_collection("stati", **schema_stati)
    stati_collection.create_index("nome", unique=True)

    schema_regioni = {
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["nome", "stato"],  # Campi obbligatori
                "properties": {
                    "nome": {
                        "bsonType": "string"  # Tipo di dato per campo1
                    },
                    "stato": {
                        "bsonType": "string"
                    }
                }
            }
        }
    }
    regioni_collection = db.create_collection("regioni", **schema_regioni)

    schema_citta = {
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["nome", "regione"],  # Campi obbligatori
                "properties": {
                    "nome": {
                        "bsonType": "string"  # Tipo di dato per campo1
                    },
                    "regione": {
                        "bsonType": "string"
                    }
                }
            }
        }
    }
    citta_collection = db.create_collection("citta", **schema_citta)

    # pasing db inaturalist inserimento dati
    with open('../../Databaseinaturalis/inaturalistOsservationsJson2023_06_14_15_37_32.json') as naturalistDB:
        dataInaturalist = json.load(naturalistDB)
        for obj in dataInaturalist:
            # non inserisco oggetti sbagliati che hanno id=id, common_name=common_name...
            if obj["id"] == "id":
                continue

            # creo collezione "insetti", "aracnidi"....
            if obj["iconic_taxon_name"] not in db.list_collection_names():
                schema_osservazione = {
                    "validator": {
                        "$jsonSchema": {
                            "bsonType": "object",
                            "required": ["data_osservazione", "image_url", "id_citta"],  # Campi obbligatori
                            "properties": {
                                "data_osservazione": {
                                    "bsonType": "string",  # Tipo di dato per campo1
                                    "pattern": "^\d{2}/\d{2}/\d{4}$"
                                },
                                "image_url": {
                                    "bsonType": "string",
                                    "pattern": "^(https?|ftp)://[^\s/$.?#].[^\s]*$"
                                },
                                "id_citta": {
                                    "bsonType": "objectId",
                                    "pattern": "^[0-9a-fA-F]{24}$"
                                    # Pattern per validare un ObjectId a 24 caratteri esadecimali
                                }
                            }
                        }
                    }
                }
                db.create_collection(obj["iconic_taxon_name"], **schema_osservazione)

            # se l'utente non è presente lo inserisco
            # if db.get_collection("utenti").find_one({"username": obj["user_name"]}) is None:
            try:
                db.get_collection("utenti").insert_one({"username": obj["user_name"], "password": "utente"})
            except:
                print(obj["user_name"] + " già presente")

            osservazione = {"data_osservazione": datetime.strptime(obj['observed_on'], "%Y-%m-%d").strftime("%d/%m/%Y"),
                            "image_url": obj['image_url'],
                            "id_citta": insert_stato_regione_citta(db, obj["place_guess"],
                                                                   obj["latitude"], obj["longitude"]),
                            "scientific_name": obj["scientific_name"]}

            db.get_collection(obj["iconic_taxon_name"]).insert_one(osservazione)
    client.close()

    return render_template('created_db.html')


def insert_stato_regione_citta(db, indirizzo, latitude, longitude):
    print(indirizzo)

    # Funzione per controllare se un elemento è presente in una collezione
    def elemento_presente(collezione, campo, valore):
        return collezione.find_one({campo: valore}) is not None

    # Funzione per inserire un nuovo elemento in una collezione
    def inserisci_elemento(collezione, elemento):
        collezione.insert_one(elemento)

    collezione_stati = db['stati']
    collezione_regioni = db['regioni']
    collezione_citta = db['citta']

    # Separazione degli elementi dell'indirizzo
    elementi = indirizzo.split(', ')
    citta, regione, stato = "", "", ""
    if len(elementi) >= 3:
        citta = elementi[-1]
        regione = elementi[-2]
        stato = elementi[-3]
    if len(elementi) == 2:
        regione = elementi[-1]
        stato = elementi[-2]
    else:
        stato = elementi[-1]

    # Verifica presenza dello stato, se non c'è stato allora non c'è ne regione ne citta
    # lo stato c'è sempre nel db
    if not elemento_presente(collezione_stati, 'nome', stato):
        inserisci_elemento(collezione_stati, {'nome': stato})
        if regione != "":
            inserisci_elemento(collezione_regioni, {'nome': regione, 'stato': stato})
            inserisci_elemento(collezione_citta,
                               {'nome': citta, 'regione': regione, 'latitudine': latitude, 'longitudine': longitude}) \
                if latitude != "" and longitude != "" else inserisci_elemento(collezione_citta,
                                                                              {'nome': citta, 'regione': regione})


    elif regione != "" and not elemento_presente(collezione_regioni, 'nome', regione):
        inserisci_elemento(collezione_regioni, {'nome': regione, 'stato': stato})
        if citta != "":
            inserisci_elemento(collezione_citta,
                               {'nome': citta, 'regione': regione, 'latitudine': latitude, 'longitudine': longitude}) \
                if latitude != "" and longitude != "" else inserisci_elemento(collezione_citta,
                                                                              {'nome': citta, 'regione': regione})

    elif not elemento_presente(collezione_citta, 'nome', citta):
        inserisci_elemento(collezione_citta,
                           {'nome': citta, 'regione': regione, 'latitudine': latitude, 'longitudine': longitude}) \
            if latitude != "" and longitude != "" else inserisci_elemento(collezione_citta,
                                                                          {'nome': citta, 'regione': regione})

    return collezione_citta.find_one({"nome": citta})["_id"]
    # Chiusura della connessione a MongoDB
    client.close()


@app.route('/registrazione')
def registrazione():
    return render_template('registrazione.html')


@app.route('/registrazione', methods=['POST'])
def inserisci_utente():
    email = request.form['email']
    password = request.form['password']

    # Crea il documento utente
    utente = {
        'email': email,
        'password': password
    }

    # Inserisci il documento nella collezione 'utenti'
    collection.insert_one(utente)

    return 'Registrazione completata con successo!'


if __name__ == '__main__':
    app.run(debug=True)
