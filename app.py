import json
import os
import random
from sched import scheduler

from bson import ObjectId
from flask import Flask, render_template, request, redirect, url_for
from pymongo import MongoClient
import re
from datetime import datetime

from pymongo.errors import DuplicateKeyError

app = Flask(__name__)

# Configurazione MongoDB
# client = MongoClient('mongodb://localhost:27017/')
# db = client['mydatabase']
# collection = db['mycollection']
UPLOAD_FOLDER = 'static'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


@app.route('/insertsegnalazione', methods=['post'])
def insert_segnalazione():
    client = MongoClient("mongodb://localhost:27017/")
    db_name = "mongoDBproject"
    db = client[db_name]
    print("insertsegn")
    file = request.files['image']

    # Salva il file nell'apposita cartella
    file.save(os.path.join(app.config['UPLOAD_FOLDER'], file.filename))
    image_url = f"{request.host_url}{UPLOAD_FOLDER}/{file.filename}"

    categoria = request.form.get('category')
    nome_scientifico = request.form.get('scientificName')
    nome_comune = request.form.get('commonName')

    # Creare un oggetto JSON con i campi principali

    osservazione = {
        'image_url': image_url,
        'scientific_name': nome_scientifico,
        'nome_comune': nome_comune,
        'data_osservazione':  datetime.strptime(request.form.get("dataosser"), "%Y-%m-%d"),
        'latitudine': float(request.form.get("latitudine")),
        'longitudine':float( request.form.get("longitudine")),

    }

    # Iterare sui parametri aggiuntivi e aggiungerli come proprietà dell'oggetto JSON
    for chiave, valore in request.form.items():
        if chiave not in ['image', 'category', 'scientificName', 'commonName', 'usernameNascosta','dataosser','latitudine','longitudine']:
            valori = valore.split(":")
            osservazione[valori[0]] = valori[1]

    id_utente= db["utenti"].find_one({"username":request.form["usernameNascosta"]})["_id"]
    osservazione["id_utente"]=ObjectId(id_utente)
    print(categoria)
    print(request.form["usernameNascosta"])
    db.get_collection(categoria).insert_one(osservazione)

    print(osservazione)

    return render_template('index.html', documents=getRandomDocuments(), benvenuto=request.form["usernameNascosta"])


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


def getCollections(db):
    collezioni = db.list_collection_names()
    collezioni_da_evitare = ['utenti', 'stati', 'regioni', 'citta']
    collezioni_filtrate = [collezione for collezione in collezioni if collezione not in collezioni_da_evitare]
    return collezioni_filtrate


def getRandomDocuments():
    client = MongoClient("mongodb://localhost:27017/")
    db_name = "mongoDBproject"
    db = client[db_name]
    # Ottenere 30 documenti casuali dalla collezione
    #    pipeline = [
    #        {'$sample': {'size': 8}}
    #    ]

    #    random_documents = {}
    #    for collection in getCollections(db):
    #        print(collection)
    #        random_documents[collection] = list(db.get_collection(collection).aggregate(pipeline))
    random_documents = {}
    for collection in getCollections(db):
        random_documents[collection] = list(db.get_collection(collection).aggregate([
            {
                '$match': {
                    '$expr': {
                        '$gt': [{'$size': {'$objectToArray': '$$ROOT'}}, 10]
                    }
                }
            },
            {
                '$sample': {
                    'size': 8
                }
            }
        ]))
    return random_documents


@app.route('/')
def index():
    return render_template('index.html', documents=getRandomDocuments())


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
                            "required": ["id_utente", "data_osservazione", "image_url", "latitudine", "longitudine"],
                            # Campi obbligatori
                            "properties": {
                                "id_utente": {
                                    "bsonType": "objectId"
                                },
                                "data_osservazione": {
                                    "bsonType": "date",  # Tipo di dato per campo1
                                    "pattern": "^\d{2}/\d{2}/\d{4}$"
                                },
                                "image_url": {
                                    "bsonType": "string",
                                    "pattern": "^(https?|ftp)://[^\s/$.?#].[^\s]*$"
                                },

                                "latitudine": {
                                    "bsonType": "double"
                                },
                                "longitudine": {
                                    "bsonType": "double"
                                }
                            }
                        }
                    }
                }
                db.create_collection(obj["iconic_taxon_name"], **schema_osservazione)

            # se l'utente non è presente lo inserisco
            # if db.get_collection("utenti").find_one({"username": obj["user_name"]}) is None:
            try:
                inserted_id = db.get_collection("utenti").insert_one(
                    {"username": obj["user_name"], "password": "utente"}).inserted_id
                print(inserted_id)
                print(inserted_id["_id"])
            except:
                inserted_id = db.get_collection("utenti").find_one({"username": obj["user_name"]})
                print(obj["user_name"] + " già presente")
                print(inserted_id)
                print(inserted_id["_id"])
            osservazione = {"id_utente": inserted_id["_id"],
                            "data_osservazione": datetime.strptime(obj['observed_on'], "%Y-%m-%d"),
                            "image_url": obj['image_url'], "latitudine": float(obj["latitude"]),
                            "longitudine": float(obj["longitude"]),
                            "scientific_name": obj["scientific_name"]}

            db.get_collection(obj["iconic_taxon_name"]).insert_one(osservazione)

    with open('../../dbinsectidentification/DBinsectidentificationJSON2.txt') as dbinsect:
        dataInsects = json.load(dbinsect)
        for obj in dataInsects:
            for collection in getCollections(db):
                scientific_name = re.sub(r'Â|\xa0', ' ', obj["scientific_name"]).strip().replace("  ", " ")
                db.get_collection(collection).update_many({"scientific_name": scientific_name},
                                                          {"$set": {"nome_comune": obj["common-name"],
                                                                    "dimensioni": obj["Size (Adult; Length)"]}})
                db.get_collection(collection).update_many({"scientific_name": scientific_name},
                                                          {"$set": creaColori(obj["Colors"])})

                try:
                    print({"scientific_name": scientific_name}, {"$set": attributi(obj["Descriptors"])})
                    if db.get_collection(collection).update_many({"scientific_name": scientific_name}, {
                        "$set": attributi(obj["Descriptors"])}).modified_count > 0:
                        print("aggiornato" + scientific_name)
                except KeyError:
                    print("descriptors key error")
    client.close()

    return render_template('created_db.html')


def attributi(stringa):
    dizionario = {
        'Bumper': 'Forma',
        'Gyrating': 'Capacità',
        'Wispy': 'Forma',
        'Salt-and-pepper': 'Pattern',
        'Royal': 'Forma',
        'Cobalt': 'Forma',
        'Borders': 'Pattern',
        'Prick': 'Pericoli',
        'Sculpted': 'Forma',
        'Stingless': 'Pericoli',
        'Butterfly-like': 'Forma',
        'Springtime': 'Benefici',
        'Warmers': 'Benefici',
        'Southeastern': 'Forma',
        'Wolves': 'Benefici',
        'Wool': 'Forma',
        'Residue': 'Pericoli',
        'Ants': 'Benefici',
        'Cryptic coloring': 'Forma',
        'Woodland': 'Benefici',
        'Female': 'Forma',
        'Wetland': 'Benefici',
        'Sideways EKG': 'Capacità',
        'ECG': 'Capacità',
        'Reallynear': 'Forma',
        'Yellowjacketshy': 'Pericoli',
        'Scared': 'Pericoli',
        'Zebra': 'Forma',
        'Chase': 'Capacità',
        'Baldshells': 'Forma',
        'Fourteen': 'Numero',
        '14': 'Numero',
        'Seven': 'Numero',
        'Pairbut': 'Pericoli',
        'Plate': 'Forma',
        'Sawdust': 'Pericoli',
        'W': 'Forma',
        'W-shape': 'Forma',
        'Elongated': 'Forma',
        'Reddish-brown': 'Colore',
        'Region': 'Forma',
        'Crab-like': 'Forma',
        'Globs': 'Forma',
        'Quick': 'Capacità',
        'Arcs': 'Forma',
        'Way': 'Benefici',
        'Two-tone': 'Colore',
        'Fur': 'Forma',
        'Frogdigging': 'Capacità',
        'Gray-brown': 'Colore',
        'Frilly': 'Forma',
        'Squishy': 'Forma',
        'Ruffle': 'Forma',
        'Edging': 'Forma',
        'Stag': 'Forma',
        'Crud': 'Pericoli',
        'Feces': 'Pericoli',
        'Leaves': 'Forma',
        'Lily': 'Forma',
        'Clearwing': 'Forma',
        'Wart': 'Forma',
        'Parasitic': 'Pericoli',
        'Jesusc-shape': 'Forma',
        'Slash': 'Forma',
        'Slant': 'Forma',
        'Brochosome': 'Forma',
        'Sidewalk': 'Forma',
        'Concrete': 'Forma',
        'Patio': 'Forma',
        'Colored': 'Colore',
        'Feathers': 'Forma',
        'Mace': 'Forma',
        'Anchor': 'Forma',
        'Wingpits': 'Forma',
        'Creamy': 'Colore',
        'Vomit': 'Pericoli',
        'Increasing size': 'Benefici',
        'Bruise': 'Pericoli',
        'Slug': 'Forma',
        'Blurry': 'Forma',
        'Sand': 'Forma',
        'Coastal': 'Forma',
        'Tidal': 'Forma',
        'Plumbing': 'Forma',
        'Pipes': 'Forma',
        'Mushrooms': 'Forma',
        'Millions': 'Numero',
        'Bugs': 'Forma',
        'Dirt': 'Forma',
        'Bluish': 'Colore',
        'Dropping': 'Pericoli',
        'Deflated': 'Forma',
        'Bend': 'Forma',
        'Flexible': 'Capacità',
        'Stones': 'Forma',
        'Firefly-like': 'Forma',
        'Bold': 'Forma',
        'Bray': 'Forma',
        'Spottingsatiny': 'Forma',
        'Claw': 'Forma',
        'Dog': 'Forma',
        'Hemlock': 'Forma',
        'Looper': 'Forma',
        'Daggers': 'Forma',
        'Flannel': 'Forma',
        'Mushroom': 'Forma',
        'Bevel': 'Forma',
        'Clicking': 'Capacità',
        'Flipping': 'Capacità',
        'Armadillo': 'Forma',
        'Wig': 'Forma',
        'Frizzy': 'Forma',
        'Crazy': 'Forma',
        'Fashion': 'Forma',
        'Squirt': 'Capacità',
        'Waste': 'Pericoli',
        'Pots': 'Forma',
        'Barrels': 'Forma',
        'Nymph': 'Forma',
        'Chartreuse': 'Colore',
        'Fingers': 'Forma',
        'Fade': 'Forma',
        'Ombré': 'Colore',
        'Orange-tipbits': 'Colore',
        'Strange': 'Forma',
        'Mat': 'Forma',
        'Cubed': 'Forma',
        'Cube': 'Forma',
        'Smear': 'Forma',
        'Stain': 'Forma',
        'Hefty': 'Forma',
        'Parts': 'Forma',
        'Bruises': 'Pericoli',
        'Segment': 'Forma',
        'Ninth': 'Numero',
        'Zucchini': 'Forma',
        'Squash': 'Forma',
        'Scar': 'Forma',
        'Tinge': 'Colore',
        'Robust': 'Forma',
        'Recluse': 'Forma',
        'Damage': 'Pericoli',
        'Stringfrom ceiling': 'Forma',
        'Stalagmite': 'Forma',
        'Stalactite': 'Forma',
        'Wall': 'Forma',
        'V-shapes': 'Forma',
        'Grayscale': 'Colore',
        'Splotch': 'Forma',
        'Button': 'Forma',
        'Walkingstick': 'Forma',
        'Dauber': 'Forma',
        'Toad': 'Forma',
        'Puzzle-shaped': 'Forma',
        'Dung': 'Pericoli',
        'Spiders': 'Forma',
        'Wedges': 'Forma',
        'Duck bill': 'Forma',
        'Fluttering': 'Capacità',
        'Screaming': 'Capacità',
        'Orange-pink': 'Colore',
        'Rolling': 'Capacità',
        'Humped': 'Forma',
        'Y-shaped': 'Forma',
        'Semicolon': 'Forma',
        'Bubbles': 'Forma',
        'Froth': 'Forma',
        'Between': 'Forma',
        'G-shaped outline': 'Forma',
        'Two-colored': 'Colore',
        'Bicolor': 'Colore',
        'Irritation': 'Pericoli',
        'Vertical arches': 'Forma',
        'Scratched': 'Pericoli',
        'Scraped': 'Pericoli',
        'Straw': 'Forma',
        'Classic': 'Forma',
        'Velvety': 'Forma',
        'Swan': 'Forma',
        'Horseshoe': 'Forma',
        'Fossil': 'Forma',
        'Trilobite': 'Forma',
        'Armour': 'Forma',
        'Biceps': 'Forma',
        'Rims': 'Forma',
        'Sparkle': 'Forma',
        'Fragile': 'Pericoli',
        'Rectangle': 'Forma',
        'Wheel': 'Forma',
        'Saw': 'Forma',
        'Spirals': 'Forma',
        'Bounce': 'Capacità',
        "diamonds": "forma",
        "large": "forma",
        "flying": "capacità",
        "harmless": "pericoli",
        "red eyes": "pattern",
        "long tail": "forma",
        "black spots on wings": "pattern",
        "banded": "pattern",
        "antennae": "forma",
        "spot": "pattern",
        "tree pest": "pericoli",
        "worn spots": "pattern",
        "black dots": "pattern",
        "white fringe": "pattern",
        "wasp": "pericoli",
        "stripes": "pattern",
        "ring": "pattern",
        "angle": "forma",
        'wide head': 'forma',
        "long antennae": "forma",
        "tiny": "forma",
        "small": "forma",
        "orange-brown head": "colore/forma",
        "band across body": "pattern",
        "worm-like with fuzzy rings": "pattern",
        "pest": "pericoli",
        "white border": "pattern",
        "edge": "forma",
        "dark spot on head": "pattern",
        "fast": "capacità",
        "water": "pericoli",
        "big": "forma",
        "brown": "colore",
        "spread out": "forma",
        "bands": "pattern",
        "venomous": "pericoli",
        "web": "pattern",
        "two rows of dots": "pattern",
        "curve line of faint spots": "pattern",
        "hairy head": "forma",
        "blue spots": "colore/pattern",
        "silver streaks": "pattern",
        "white": "colore",
        "pattern": "pattern",
        "colorful hindwings": "pattern",
        "stripe": "pattern",
        "tail": "forma",
        "spine": "forma",
        "clusters": "pattern",
        "wood wasp": "pericoli",
        "beneficial": "benefits",
        "helpful": "benefits",
        "fuzzy": "forma",
        "skinny": "forma",
        "lines": "pattern",
        "texture": "pattern",
        "ridges": "forma",
        "pink purple head": "colore/forma",
        "pink kneecaps": "colore/forma",
        "brown wings": "colore/forma",
        "rosy antennae": "colore/forma",
        "jumping": "capacità",
        "multicolored": "colore",
        "bright": "colore",
        "middle white band": "pattern",
        "yellow bottom": "colore/forma",
        "olive green": "colore/forma",
        "silver": "colore",
        "black upper body": "colore/forma",
        "two light bands": "pattern",
        "black spots": "pattern",
        "random": "pattern",
        "black wing tips": "pattern",
        "blue body": "colore/forma",
        "painted": "pattern",
        "dragonfly": "forma",
        "yellow bands": "pattern",
        "veins": "pattern",
        "bright hindwing": "pattern",
        "fuchsia": "colore",
        "pointed wings": "forma",
        "bug": "forma",
        "streamlined": "forma",
        "biting": "pericoli",
        "itch": "pericoli",
        "feathery antennae": "forma",
        "chirp": "capacità",
        "striped": "pattern",
        "lined": "pattern",
        "red": "colore",
        "furry": "forma",
        "hairy": "forma",
        "sensitive": "capacità",
        "allergic": "pericoli",
        "wavy": "forma",
        "yellow on tip of tail": "colore/forma",
        "many yellow marks by 'shoulders'": "pattern",
        "black body": "colore/forma",
        "yellow stripe": "pattern",
        "band": "pattern",
        "orange eyespots": "pattern",
        "blue row on wings": "pattern",
        "bee": "pericoli",
        "triangle": "forma",
        "harmful": "pericoli",
        "stinging": "pericoli",
        "fat": "forma",
        "painful": "pericoli",
        "tentacles": "forma",
        "legs": "forma",
        "rows of white spots": "pattern",
        "orange bottom spots": "pattern",
        "orange rim border": "pattern",
        "large orange spots by head": "pattern",
        "black center": "pattern",
        "nose": "forma",
        "hairy face": "forma",
        "long nose": "forma",
        "snout": "forma",
        "streak": "pattern",
        "patterned": "pattern",
        "orange rows": "pattern",
        "yellow row": "pattern",
        "white spots underneath": "pattern",
        "pacific northwest": "pattern",
        "checkers": "pattern",
        "black mark": "pattern",
        "wings": "forma",
        "circles": "pattern",
        "orange": "colore",
        "velvet": "pattern",
        "colorful": "colore"
        ,
        "huge": "forma",
        "long": "forma",
        "bumpy": "forma",
        "flocking": "comportamento",
        "chewing": "comportamento",
        "pine tree": "forma",
        "red dots": "pattern",
        "red mites": "pattern",
        "powder": "forma",
        "neck point": "forma",
        "thorns": "forma",
        "long legs": "forma",
        "aquatic": "forma",
        "swimming pool": "forma",
        "backstroke": "comportamento",
        "spider-like": "forma",
        "floating": "comportamento",
        "bobbing": "comportamento",
        "head down in water": "comportamento",
        "feathery feet": "forma",
        "swimming": "comportamento",
        "black head": "colore/forma",
        "gray wings": "colore/forma",
        "short black slits": "pattern",
        "worm in case": "forma",
        "pine needles": "forma",
        "lichen dead plant": "pattern",
        "litter": "pattern",
        "crawling": "comportamento",
        "speckled": "pattern"
        , "fang": "forma",
        "long and skinny": "forma",
        "leaf": "forma",
        "criss-crossed lines": "pattern",
        "salmon pink hindwing": "colore/forma",
        "furry, hairy thorax": "forma",
        "all black or striped 'shoulders'": "pattern",
        "slender": "forma",
        "pointy spiky shoulders": "forma",
        "wide orange bands": "pattern",
        "group": "comportamento",
        "flowers": "forma",
        "orange and black wings": "colore/forma",
        "brown hairy body": "colore/forma",
        "black half moons on bottom of wings": "pattern",
        "checkered fringe": "pattern",
        "split wings": "forma",
        "brown specks": "pattern",
        "yellow wings": "colore/forma",
        "purple shading": "colore/forma",
        "shiny": "forma",
        "metallic": "forma",
        "green": "colore/forma",
        "yellow legs": "colore/forma",
        "red bar on wings": "pattern",
        "skimmer": "comportamento",
        "blue band": "pattern",
        "turquoise": "colore/forma",
        "skinny tail": "forma",
        'pointy': 'forma',
        'holes': 'pattern',
        'thorny': 'forma',
        'spiny': 'forma',
        'arrow': 'forma',
        'pyramid': 'forma',
        'patch': 'pattern',
        'tucked': 'forma',
        'round thorax': 'forma',
        'long streaks on wing': 'pattern',
        'dark hindwing': 'pattern',
        'white spots': 'pattern',
        'trio': 'pattern',
        'triplet': 'pattern',
        'beige': 'forma',
        'spots': 'pattern',
        'dots': 'pattern',
        'signate': 'pattern',
        'stabbed': 'pericolo',
        'round': 'forma',
        'dome': 'forma',
        'helmet': 'forma',
        'spiky': 'forma',
        'alligator': 'forma',
        'enormous': 'forma',
        'banding': 'pattern',
        'invasive': 'pericolo',
        'hairs': 'forma',
        'tinted wings': 'pattern',
        'firefly': 'forma',
        'slow': 'capacità',
        'ladybug': 'forma',
        'smelly': 'pericolo',
        'mouth': 'forma',
        'lines on wings': 'pattern',
        'black underneath': 'pattern',
        'stabbing': 'pericolo',
        'piercing': 'pericolo',
        'plain': 'forma',
        'fluffy': 'forma',
        'comma marks': 'pattern',
        'orange tip': 'pattern',
        'orange face': 'pattern',
        'stinging caterpillar': 'pericolo',
        'narrow': 'forma',
        'orange middle': 'pattern',
        'black and white legs': 'pattern',
        'brown body': 'forma',
        'v-shape': 'forma',
        'U line': 'pattern',
        'tail up': 'forma',
        'red dot caterpillar': 'pattern',
        'flattened body': 'forma',
        'trunk': 'forma',
        'pale': 'forma',
        'bathroom': 'forma',
        'white round spot': 'pattern',
        'dark wings': 'pattern',
        'dark dashes': 'pattern',
        'white stripes': 'pattern',
        'silver lines': 'pattern',
        'flesh-colored': 'forma',
        'clear wings': 'forma',
        'half': 'forma',
        'sweat': 'forma',
        'drink': 'forma',
        'two': 'forma',
        'pollinator': 'forma',
        'tubular': 'forma',
        'thin': 'forma',
        'rings': 'pattern',
        'white curves': 'pattern',
        'white crescents': 'pattern',
        'purple wave': 'pattern',
        'corner marks': 'pattern',
        'curled': 'forma',
        'curvy': 'forma',
        'long snout': 'forma',
        'triangle shape': 'forma',
        'spotted': 'pattern',
        'flower': 'forma',
        'flared': 'forma',
        'raised': 'forma',
        'sides': 'forma',
        'dark brown or black wings': 'pattern',
        'tan head and middle': 'pattern',
        'fork': 'forma',
        'side stripes': 'pattern',
        'taupe': 'forma',
        'stinger': 'pericolo',
        'mark': 'pattern',
        'wide': 'forma',
        'infestation': 'pericolo',
        'two-toned': 'pattern',
        'fringe': 'pattern',
        'tick': 'pericolo',
        'blood': 'pericolo',
        'trio of dots': 'pattern',
        'triangle dot': 'pattern',
        'three point triangle': 'pattern',
        'dotted bottom line': 'pattern',
        'polka dot': 'pattern',
        'Dalmatian': 'pattern',
        'red feet': 'pattern',
        'red legs': 'pattern',
        'tube': 'forma',
        'rounded': 'forma',
        'red bands': 'pattern',
        'armor plated': 'pattern',
        'curl': 'forma',
        'curve': 'forma',
        'mottled': 'pattern',
        'bee-like': 'forma',
        'wasp mimic': 'forma',
        'hovering': 'capacità',
        'short lines': 'pattern',
        'bronze': 'forma',
        'orange spot': 'pattern',
        'lichen': 'pattern',
        'eyespots': 'pattern',
        'lady': 'forma',
        'four legs': 'capacità',
        'hind wings': 'forma',
        'flat': 'forma',
        'flare': 'forma',
        'side wings': 'forma',
        'stick out': 'forma',
        'scalloped lines': 'pattern',
        'rusty orange torso': 'forma',
        'black bottom': 'pattern',
        'black': 'forma',
        'rough': 'forma',
        'blister': 'pericolo',
        'burn': 'pericolo',
        'thighs': 'forma',
        'thin abdomen': 'forma',
        'bright spot on wings': 'pattern',
        'long furry nose': 'forma',
        'jagged wings': 'forma',
        'orange patches': 'pattern',
        'luster': 'forma',
        'iridescent': 'forma',
        'bumpy lines': 'pattern',
        'long narrow head': 'forma',
        'copper': 'forma',
        'gold': 'forma',
        'flecks': 'pattern',
        'yellow': 'forma',
        'caterpillar': 'forma',
        'wire': 'forma',
        'oak': 'forma',
        'wing tail': 'forma',
        'dark body': 'forma',
        'wide band': 'pattern',
        'eyespots by rear end': 'pattern',
        'scalloped': 'forma',
        'black antennae': 'pattern',
        'underground': 'capacità',
        'mud': 'forma',
        'kitchen': 'forma',
        'ant-like': 'forma',
        'ant': 'forma',
        'white lines': 'pattern',
        'diagonal': 'forma',
        'big wide head': 'forma',
        'shoulder bumps': 'forma',
        'black wide head': 'forma',
        'rectangular or squared head': 'forma',
        'pinchers': 'forma',
        'big, curved jaws': 'forma',
        'smooth head': 'forma',
        'dimpled body': 'forma',
        'dragonfly-like': 'forma',
        'markings': 'pattern',
        'tips': 'forma',
        'tracks': 'pattern',
        'doodlebug': 'forma',
        'wide eyes': 'forma',
        'jaws': 'forma',
        'spikes': 'forma',
        'jump': 'capacità',
        'garden pest': 'pericolo',
        'commas': 'pattern',
        'dashes': 'pattern',
        'pointed bar': 'pattern',
        'upside down': 'forma',
        'dot': 'pattern',
        'line': 'pattern',
        'point': 'forma',
        'downward': 'forma',
        'drip': 'forma',
        'tip': 'forma',
        'hook': 'forma',
        'beak': 'forma',
        'smooth': 'forma',
        'stealth': 'capacità',
        'nocturnal': 'capacità',
        'marbled': 'pattern',
        'small orange spots': 'pattern',
        'brown rings': 'pattern',
        'scallop': 'forma',
        'white line across': 'pattern',
        'dark purple': 'forma',
        'maroon': 'forma',
        'wine': 'forma',
        'white patch': 'pattern',
        'dark border edge': 'pattern',
        'many spots': 'pattern',
        'rounded wings': 'forma',
        'checkered': 'pattern',
        'chequered': 'pattern',
        'tan edges': 'pattern',
        'reniform spots': 'pattern',
        'tooth border': 'pattern',
        'round spots': 'pattern'
    }

    def cerca_in_dizionario(stringa, dizionario):
        risul = []
        parole = stringa.split(';')
        for parola in parole:
            parola = parola.strip()
            if parola in dizionario:
                risul.append({dizionario[parola]: parola})

        return risul

    risultati = cerca_in_dizionario(stringa, dizionario)

    oggetto_json = json.dumps(risultati)
    print(unisci_oggetti(rimuovi_chiavi_duplicate(oggetto_json)).replace("\\u00e0", "a"))
    return json.loads(unisci_oggetti(rimuovi_chiavi_duplicate(oggetto_json)).replace("\\u00e0", "a"))


@app.route("/viewSegnalazione", methods=["GET"])
def visualizza_documento():
    # Ottieni il valore del parametro "id" dalla richiesta GET
    documento_id = request.args.get("id")
    client = MongoClient('mongodb://localhost:27017/')
    db = client['mongoDBproject']
    documento = None
    for collezione in getCollections(db):
        try:

            documento = db.get_collection(collezione).aggregate([
                {
                    '$match': {
                        '_id': ObjectId(documento_id)
                    }
                },
                {
                    '$lookup': {
                        'from': 'utenti',
                        'localField': 'id_utente',
                        'foreignField': '_id',
                        'as': 'utente'
                    }
                },
                {
                    '$project': {

                        'utente.password': 0,
                        'utente._id': 0,

                        'id_utente': 0
                    }
                }
            ]).next()

        except StopIteration:
            continue

        # Cerca il documento corrispondente nell'archivio dei dati
        # documento = db.get_collection(collezione).find_one({"_id": ObjectId(documento_id)})
        print(documento)
       # print()
        if documento is not None:
            return render_template("segnalazione.html", documento=documento, admin= True if request.args.get("admin")=='true' else False)

    return render_template("errore.html", messaggio="nessun doc con id:" + documento_id)
    # Passa il documento alla pagina HTML come contesto


def unisci_oggetti(json_array):
    # Carica l'array JSON in una lista di oggetti Python
    array = json.loads(json_array)

    # Crea un nuovo dizionario per contenere le coppie chiave-valore combinate
    merged_dict = {}

    # Itera sugli oggetti nella lista
    for obj in array:
        # Estrai le coppie chiave-valore dall'oggetto
        for key, value in obj.items():
            # Aggiungi la coppia chiave-valore al dizionario combinato
            merged_dict[key] = value

    # Converti il dizionario combinato in una stringa JSON
    json_risultante = json.dumps(merged_dict)

    return json_risultante


def rimuovi_chiavi_duplicate(json_data):
    # Carica la stringa JSON in un oggetto Python
    data = json.loads(json_data)

    # Rimuovi le chiavi duplicate
    data = rimuovi_duplicate(data)

    # Converti l'oggetto Python in una stringa JSON
    json_risultante = json.dumps(data)

    return json_risultante


def rimuovi_duplicate(obj):
    # Verifica se l'oggetto è un dizionario
    if isinstance(obj, dict):
        # Rimuovi le chiavi duplicate
        obj = {k: rimuovi_duplicate(v) for k, v in obj.items()}

    # Verifica se l'oggetto è una lista
    elif isinstance(obj, list):
        # Rimuovi le chiavi duplicate dagli elementi della lista
        obj = [rimuovi_duplicate(elem) for elem in obj]

    return obj


def creaColori(color_string):
    def create_color_associations(colors, strings):
        random.shuffle(strings)
        random.shuffle(colors)
        associations = {}

        num_associations = random.randint(1, len(strings))
        for i in range(num_associations):
            string = strings[i]
            color = colors[i % len(colors)]
            associations[string] = color

        return associations

    color_list = [color.strip() for color in color_string.split(";")]
    string_list = ["Colore principale", "Sfumatura", "Colore secondario", "Colore traslucido",
                   "Colore dei tergiti", "Colore inferiore", "Colore superiore"]

    associations = create_color_associations(color_list, string_list)

    json_data = json.dumps(associations)

    print(json_data)
    return json.loads(json_data)


@app.route('/registrazione')
def registrazione():
    return render_template('registrazione.html')


@app.route('/registrazione', methods=['POST'])
def inserisci_utente():
    client = MongoClient("mongodb://localhost:27017/")
    db_name = "mongoDBproject"
    db = client[db_name]
    username = request.form['username']
    password = request.form['password']

    # Crea il documento utente
    utente = {
        'username': username,
        'password': password
    }
    print(utente)
    # Inserisci il documento nella collezione 'utenti'
    try:
        db.get_collection("utenti").insert_one(utente)
    except DuplicateKeyError:
        client.close()
        return render_template("registrazione.html", giaPresente=username)

    return render_template("index.html", documents=getRandomDocuments(), benvenuto=username)


@app.route('/cercaSegnalazioni', methods=['POST'])
def cercaSegnalazioni():
    # Funzione per creare una query MongoDB in base ai parametri
    def build_query(inizio_data, fine_data, latitudine, longitudine, nome_scientifico):
        query = {}

        if inizio_data and fine_data:
            query['data_osservazione'] = {'$gte': datetime.strptime(inizio_data, '%Y-%m-%d'),
                                          '$lte': datetime.strptime(fine_data, '%Y-%m-%d')}
        elif inizio_data and not fine_data:
            query['data_osservazione'] = {'$gte': inizio_data}

        elif fine_data and not inizio_data:
            query['data_osservazione'] = {'$lte': fine_data}

        if latitudine:
            lat = float(latitudine)
            query['latitudine'] = {'$gte': lat - 10, '$lte': lat + 10}

        if longitudine:
            lon = float(longitudine)
            query['longitudine'] = {'$gte': lon - 10, '$lte': lon + 10}

        if nome_scientifico:
            query['scientific_name'] = {'$regex': re.compile(re.escape(nome_scientifico), re.IGNORECASE)}

        return query

    # Eseguire la query nel database
    def execute_query(query):
        client = MongoClient("mongodb://localhost:27017/")
        database = client['mongoDBproject']

        rst = {}
        for collection in getCollections(database):
            rst[collection] = list(database[collection].find(query, {'_id': 0, 'id_utente': 0}))

        return rst

    inizio_data = request.form.get('inizioData')
    fine_data = request.form.get('fineData')
    latitudine = request.form.get('latitudine')
    longitudine = request.form.get('longitudine')
    nome_scientifico = request.form.get('nomeScientifico')

    username_utente = request.form.get('usernameUtente')

    query = build_query(inizio_data, fine_data, latitudine, longitudine, nome_scientifico)
    print(query)
    result = execute_query(query)
    print(result)
    return render_template("segnalazioniTrovate.html", data=result, query=query)


@app.route('/cercaUsername', methods=['POST'])
def cercaUsername():
    client = MongoClient("mongodb://localhost:27017/")
    db = client['mongoDBproject']

    # Crea la pipeline di aggregazione
    pipeline = [
        {
            "$lookup": {
                "from": "utenti",
                "localField": "id_utente",
                "foreignField": "_id",
                "as": "utente"
            }
        },
        {
            "$match": {
                "utente.username": request.form["usernameUtente"]
            }
        },
        {
            "$project": {
                "_id": 0,
                "id_utente":0,
                "utente.password":0,
                "utente._id":0
            }
        }
    ]
    print(pipeline)
    # Esegui la query di aggregazione
    risultati={}
    for collection in getCollections(db):
        risultati[collection] = list(db.get_collection(collection).aggregate(pipeline))
    print(risultati)

    return render_template("segnalazioniTrovateUsername.html", data=risultati, query=pipeline)

@app.route('/login')
def login():
    return render_template("login.html")


@app.route('/checklogin', methods=['POST'])
def checklogin():
    client = MongoClient("mongodb://localhost:27017/")
    db_name = "mongoDBproject"
    db = client[db_name]

    username = request.form['username']
    password = request.form['password']

    # Query MongoDB to find the user
    user = db["utenti"].find_one({'username': username, 'password': password})

    if user:
        return render_template('index.html', documents=getRandomDocuments(), benvenuto=username)
    else:
        return render_template('login.html', login=False)


@app.route('/cancella', methods=['GET'])
def elimina_documento():
    id_documento = request.args.get('id')
    print(id_documento)
    client = MongoClient("mongodb://localhost:27017/")
    db_name = "mongoDBproject"
    db = client[db_name]
    if id_documento:
        for collection in getCollections(db):
            result = db[collection].delete_one({'_id': ObjectId(id_documento)})
            if result.deleted_count == 1:
                return render_template('index.html', documents=getRandomDocuments(), benvenuto="admin", cancellato=True)

    else:
        return 'ID documento mancante'

@app.route('/modifica', methods=['GET'])
def get_document():
        client = MongoClient("mongodb://localhost:27017/")
        db_name = "mongoDBproject"
        db = client[db_name]
        document_id = request.args.get('id')
        for collezione in getCollections(db):
            document = db[collezione].find_one({'_id': ObjectId(document_id)})
            if document:
                return render_template('modifica.html', document=document)

        return render_template('index.html')

@app.route('/modificaDoc', methods=['POST'])
def update_document():
    client = MongoClient("mongodb://localhost:27017/")
    db_name = "mongoDBproject"
    db = client[db_name]

    document_id = request.form['_id']
    document_fields = request.form.to_dict()
    print(document_fields)
    document_fields.pop('_id')  # Rimuovi l'ID dal dizionario dei campi
    document_fields.pop('id_utente')
    document_fields['data_osservazione'] = datetime.strptime(document_fields['data_osservazione'], "%Y-%m-%d %H:%M:%S")
    document_fields['latitudine'] = float(document_fields['latitudine'])
    document_fields['longitudine'] = float(document_fields['longitudine'])

    for collection in getCollections(db):
        db[collection].update_one({'_id': ObjectId(document_id)}, {'$set': document_fields})
    return render_template('index.html', documents=getRandomDocuments(), benvenuto="admin", modificato=True)


if __name__ == '__main__':
    app.run(debug=True)
