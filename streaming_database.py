# Bibliotheken importieren
import os  # Betriebssystem-Funktionen
import sqlalchemy as db  # SQL Toolkit
from sqlalchemy import select, func, desc
import pandas as pd # Datenverarbeitung (pandas)

# Basisverzeichnis dieses Skripts fuer relative Datei-Pfade
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Datenbankpfad
db_path = os.path.join(BASE_DIR, "streaming.db")

# Reproduzierbarkeit sicherstellen
# Bestehende Datenbank ggf. loeschen
if os.path.exists(db_path):
    os.remove(db_path)

# Zentrales Engine-Objekt zur Verbindung mit SQLite-Datenbank erzeugen
engine = db.create_engine(f"sqlite:///{db_path}")

# MetaData-Objekt als Container fuer das Datenbankschema erstellen
meta_data = db.MetaData()

# Tabelle "Movies" definieren
movies = db.Table(
    "movies", meta_data,
    db.Column("id", db.Integer, primary_key=True,
              autoincrement=True, nullable=False),
    db.Column("title", db.String(50), nullable=False),
    db.Column("genre", db.String(50), nullable=False),
    db.Column("duration_min", db.Integer, nullable=False),
    db.Column("release_year", db.Integer, nullable=False))

# Tabelle "Users" definieren
users = db.Table(
    "users", meta_data,
    db.Column("id", db.Integer, primary_key=True,
              autoincrement=True, nullable=False),
    db.Column("username", db.String(50), nullable=False),
    db.Column("subscription_type", db.String(50), nullable=False),
    db.Column("age", db.Integer, nullable=False)
)

# Tabelle "User Interactions" definieren
user_interactions = db.Table(
    "user_interactions", meta_data,
    db.Column("id", db.Integer, primary_key=True,
              autoincrement=True, nullable=False),
    db.Column("user_id", db.Integer, nullable=False),
    db.Column("movie_id", db.Integer, nullable=False),
    db.Column("rating_value", db.Integer, nullable=False),
    db.Column("view_time", db.Integer, nullable=False)
)

# Funktion: Initialisierung des Datenbankschemas
def create_schema():

    # Bestehende Tabellen entfernen (Reset)
    meta_data.drop_all(engine)

    # Tabellen gemaess Definition im MetaData-Objekt erzeugen
    meta_data.create_all(engine)

# Funktion: Filme (manuell) in Tabelle "Movies" einfuegen
def insert_movies():

    # Filmdaten als Liste von Dictionary-Eintraegen definieren
    movie_list = [
        {"id": 1, "title": "Titanic", "genre": "Drama",
            "duration_min": 195, "release_year": 1997},
        {"id": 2, "title": "The Dark Knight", "genre": "Action",
            "duration_min": 152, "release_year": 2008},
        {"id": 3, "title": "Avatar", "genre": "Science Fiction",
            "duration_min": 162, "release_year": 2009},
        {"id": 4, "title": "The Avengers", "genre": "Action",
            "duration_min": 143, "release_year": 2012},
        {"id": 5, "title": "Inception", "genre": "Science Fiction",
            "duration_min": 148, "release_year": 2010},
        {"id": 6, "title": "Jurassic World", "genre": "Adventure",
            "duration_min": 124, "release_year": 2015}
    ]

    # Verbindung zur Datenbank herstellen
    connection = engine.connect()

    # Daten in die Tabelle einfuegen
    connection.execute(movies.insert(), movie_list)

    # Aenderungen dauerhaft speichern
    connection.commit()

# Funktion: User-Daten aus CSV einlesen und in Tabelle "Users" speichern
def import_insert_users():

    # CSV-Datei in DataFrame laden (Trennzeichen: Semikolon)
    user_data = pd.read_csv(os.path.join(BASE_DIR, "users_db.csv"), sep=";")

    # DataFrame in Liste von Dictionary-Eintraegen umwandeln
    user_list = user_data.to_dict(orient="records")

    # Verbindung zur Datenbank herstellen
    connection = engine.connect()

    # Daten in die Tabelle einfuegen
    connection.execute(users.insert(), user_list)

    # Aenderungen dauerhaft speichern
    connection.commit()

# Funktion: Interaktionsdaten aus CSV einlesen und in Tabelle "User Interactions" speichern (analog import_insert_users)
def import_insert_interactions():

    user_interaction_data = pd.read_csv(os.path.join(BASE_DIR, "user_interactions_db.csv"), sep=";")
    user_interaction_list = user_interaction_data.to_dict(orient="records")
    connection = engine.connect()
    connection.execute(user_interactions.insert(), user_interaction_list)
    connection.commit()

# Funktion: Durchschnittsalter der Nutzer berechnen und ausgeben (Abfrage 1)
def avg_age_users():

    # SQL-Abfrage zur Berechnung des Durchschnittsalters definieren
    stmt = select(func.avg(users.c.age))

    # Verbindung zur Datenbank herstellen und Abfrage ausfuehren
    with engine.connect() as connection:
        result = connection.execute(stmt)

        # Ergebnis in einzelnen Wert ueberfuehren
        users_age_avg = result.scalar()

        # Ergebnis ausgeben
        print("Abfrage 1: Durchschnittsalter der Nutzer\n")
        print(f"Durchschnittsalter der Nutzer: {users_age_avg} Jahre\n")

# Funktion: Durchschnittliche Bewertung pro Film berechnen und ausgeben (Abfrage 2)
def avg_rating_per_movie():

    # SQL-Abfrage zur Berechnung der durchschnittlichen Bewertung pro Film definieren
    stmt = (
        select(
            movies.c.title,
            func.round(func.avg(user_interactions.c.rating_value),
                       2).label("avg_rating")
        )

        # Tabellen ueber Film-ID verknuepfen (INNER JOIN)
        .join(user_interactions, movies.c.id == user_interactions.c.movie_id)

        # Gruppierung nach Filmtitel
        .group_by(movies.c.title)

        # Ergebnisse absteigend nach durchschnittlicher Bewertung sortieren
        .order_by(desc("avg_rating"))
    )

    # Verbindung zur Datenbank herstellen und Abfrage ausfuehren
    with engine.connect() as connection:
        result = connection.execute(stmt)

        # Ergebnis zeilenweise ausgeben
        print("Abfrage 2: Durchschnittliche Bewertung pro Film\n")
        for row in result:
            print(f"{row.title}: {row.avg_rating}")
        print()

# Funktion: Bestbewerteten Film pro Vertragstyp ermitteln (Abfrage 3)
def best_movie_per_subscription():

    # Aliase fuer bessere Lesbarkeit bei komplexeren Joins
    m = movies.alias("m")
    u = users.alias("u")
    ui = user_interactions.alias("ui")

    # Subquery: Durchschnittsbewertung je Film und Vertragstyp sowie Ranking berechnen
    subq_stmt = (
        select(
            u.c.subscription_type,
            m.c.title,
            func.round(func.avg(ui.c.rating_value), 2).label("avg_rating"),
            func.rank().over(
                partition_by=u.c.subscription_type,
                order_by=func.avg(ui.c.rating_value).desc()
            ).label("ranking")
        )
        .join(m, ui.c.movie_id == m.c.id)
        .join(u, ui.c.user_id == u.c.id)
        .group_by(u.c.subscription_type, m.c.title)
    )

    # Subquery als Grundlage fuer Filterung verwenden (nur Rang 1)
    subq = subq_stmt.subquery()

    stmt = (
        select(
            subq.c.subscription_type,
            subq.c.title,
            subq.c.avg_rating
        )
        .where(subq.c.ranking == 1)
    )

    # Verbindung zur Datenbank herstellen und Abfrage ausfuehren
    with engine.connect() as connection:
        result = connection.execute(stmt)

        # Ergebnisse ausgeben
        print("Abfrage 3: Bester Film pro Vertragstyp\n")
        for row in result:
            print(row)
        print()

# Funktion: Filme mit ueberdurchschnittlicher Bewertung und Sehdauer ermitteln (Abfrage 4)
def above_avg_movies():

    # Aliase fuer bessere Lesbarkeit bei der Verwendung mehrerer Tabellen
    m = movies.alias("m")
    ui = user_interactions.alias("ui")

    # Globale Durchschnittswerte als Subqueries definieren (entspricht den Subqueries im HAVING-Teil der SQL-Abfrage)
    global_avg_rating = select(
        func.avg(user_interactions.c.rating_value)
    ).scalar_subquery() # liefert einen einzelnen Vergleichswert

    global_avg_view_time = select(
        func.avg(user_interactions.c.view_time)
    ).scalar_subquery()

    # Hauptabfrage: Durchschnittswerte je Film berechnen
    stmt = (
        select(
            m.c.title,
            func.round(func.avg(ui.c.rating_value), 2).label("avg_rating"),
            func.round(func.avg(ui.c.view_time), 2).label("avg_view_time")
        )

        # Tabellen verknuepfen (Join ueber movie_id)
        .join(ui, m.c.id == ui.c.movie_id)

        # Aggregation auf Filmebene
        .group_by(m.c.title)

        # Filter auf aggregierte Werte (HAVING-Bedingungen)
        # Auswahl nur der Filme ueber dem globalen Durchschnitt
        .having(func.avg(ui.c.rating_value) > global_avg_rating)
        .having(func.avg(ui.c.view_time) > global_avg_view_time)
    )

    # Verbindung zur Datenbank herstellen und Abfragen ausfuehren
    with engine.connect() as connection:

        # Globale Durchschnittswerte separat berechnen (fuer Ausgabe / Vergleich)
        global_values = connection.execute(
            select(
                func.round(func.avg(user_interactions.c.rating_value), 2).label("avg_rating_all"),
                func.round(func.avg(user_interactions.c.view_time), 2).label("avg_view_time_all")
            )
        ).one() # erwartet genau eine Ergebniszeile

        print("Abfrage 4: Filme mit ueberdurchschnittlicher Bewertung und Sehdauer\n")

        # Ausgabe der globalen Referenzwerte
        print("Durchschnittliche Bewertung aller Filme:", global_values.avg_rating_all)
        print(f"Durchschnittliche Sehdauer aller Filme: {global_values.avg_view_time_all} Minuten\n")

        # Ausgabe der gefilterten Filme (Hauptabfrage)
        print("Filme mit ueberdurchschnittlicher Bewertung und Sehdauer:\n")

        # Hauptabfrage ausfuehren
        result = connection.execute(stmt)

        # Iteration ueber alle Ergebniszeilen
        for row in result:

            # Formatierte Ausgabe der Ergebnisse je Film
            print(
                f"{row.title} | "
                f"Durchschnittliche Bewertung: {row.avg_rating} | "
                f"Durchschnittliche Sehdauer: {row.avg_view_time} Minuten"
            )
        print()

# Hauptfunktion
def main():
    create_schema()
    insert_movies()
    import_insert_users()
    import_insert_interactions()

    print("\nAnalyse und Auswertung der Filmdatenbank:\n")

    avg_age_users()
    avg_rating_per_movie()
    best_movie_per_subscription()
    above_avg_movies()

if __name__ == "__main__":
    main()