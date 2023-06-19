import json
import random

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
    pipeline = [
        {'$sample': {'size': 8}}
    ]

    random_documents = {}
    for collection in getCollections(db):
        print(collection)
        random_documents[collection] = list(db.get_collection(collection).aggregate(pipeline))
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

    with open('../../dbinsectidentification/DBinsectidentificationJSON2.txt') as dbinsect:
        dataInsects = json.load(dbinsect)
        for obj in dataInsects:
            for collection in getCollections(db):
                db.get_collection(collection).update_many({"scientific_name": obj["scientific_name"]},
                                                          {"$set": {"nome_comune": obj["common-name"],
                                                                    "dimensioni": obj["Size (Adult; Length)"]}})
                db.get_collection(collection).update_many({"scientific_name": obj["scientific_name"]},{"$set":creaColori(obj["Colors"])})

                try:
                    db.get_collection(collection).update_many({"scientific_name": obj["scientific_name"]},{"$set":attributi(obj["Descriptors"])})
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
                risul.append({dizionario[parola]:parola})

        return risul

    risultati = cerca_in_dizionario(stringa, dizionario)

    oggetto_json = json.dumps(risultati)
    print(unisci_oggetti(rimuovi_chiavi_duplicate(oggetto_json)))
    return json.loads(unisci_oggetti(rimuovi_chiavi_duplicate(oggetto_json)))

@app.route("/viewSegnalazione", methods=["GET"])
def visualizza_documento():
    # Ottieni il valore del parametro "id" dalla richiesta GET
    documento_id = request.args.get("id")
    client = MongoClient('mongodb://localhost:27017/')
    db = client['mydatabase']
    documento = None
    for collezione in getCollections(db):
        # Cerca il documento corrispondente nell'archivio dei dati
        documento = db.get_collection(collezione).find_one({"_id": ObjectId(documento_id)})
        if documento is not None:
            return render_template("segnalazione.html", documento=documento)


    return render_template("errore.html", messaggio="nessun doc con id:"+documento_id)
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


if __name__ == '__main__':
    app.run(debug=True)
