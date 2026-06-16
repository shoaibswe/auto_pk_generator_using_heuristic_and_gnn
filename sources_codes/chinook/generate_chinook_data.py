import os
import random
import csv
from datetime import date, timedelta

random.seed(42)
OUT_DIR = "./data"
os.makedirs(OUT_DIR, exist_ok=True)


def write_csv(filename, header, rows):
    path = os.path.join(OUT_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"  {filename}: {len(rows)} rows")


def rand_date(start, end):
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


# ============ Word pools for realistic data ============
FIRST_NAMES = [
    "James", "Mary", "Robert", "Patricia", "John", "Jennifer", "Michael",
    "Linda", "David", "Barbara", "William", "Elizabeth", "Richard", "Susan",
    "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen", "Daniel",
    "Lisa", "Matthew", "Nancy", "Anthony", "Betty", "Mark", "Margaret",
    "Donald", "Sandra", "Steven", "Ashley", "Paul", "Kimberly", "Andrew",
    "Emily", "Joshua", "Donna", "Kenneth", "Michelle", "Kevin", "Carol",
    "Brian", "Amanda", "George", "Dorothy", "Timothy", "Melissa", "Ronald",
    "Deborah", "Edward", "Stephanie", "Jason", "Rebecca", "Jeffrey", "Sharon",
    "Ryan", "Laura", "Jacob", "Cynthia", "Gary", "Kathleen", "Nicholas",
    "Amy", "Eric", "Angela", "Jonathan", "Shirley", "Stephen", "Anna",
    "Larry", "Brenda", "Justin", "Pamela", "Scott", "Emma", "Brandon",
    "Nicole", "Benjamin", "Helen", "Samuel", "Samantha", "Raymond", "Katherine",
    "Gregory", "Christine", "Frank", "Debra", "Alexander", "Rachel", "Patrick",
    "Carolyn", "Jack", "Janet", "Dennis", "Catherine", "Jerry", "Maria",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts", "Gomez", "Phillips", "Evans", "Turner", "Diaz",
    "Parker", "Cruz", "Edwards", "Collins", "Reyes", "Stewart", "Morris",
    "Morales", "Murphy", "Cook", "Rogers", "Gutierrez", "Ortiz", "Morgan",
]

CITIES = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix", "Philadelphia",
    "San Antonio", "San Diego", "Dallas", "San Jose", "Austin", "Jacksonville",
    "Fort Worth", "Columbus", "Charlotte", "Indianapolis", "San Francisco",
    "Seattle", "Denver", "Nashville", "London", "Paris", "Berlin", "Tokyo",
    "Sydney", "Toronto", "Montreal", "Vancouver", "Dublin", "Edinburgh",
    "Oslo", "Stockholm", "Helsinki", "Copenhagen", "Amsterdam", "Brussels",
    "Vienna", "Prague", "Warsaw", "Budapest", "Lisbon", "Madrid", "Barcelona",
    "Rome", "Milan", "Athens", "Ankara", "Cairo", "Mumbai", "Shanghai",
]

STATES = [
    "NY", "CA", "IL", "TX", "AZ", "PA", "FL", "OH", "NC", "IN",
    "WA", "CO", "TN", "ON", "QC", "BC", "AB", "NSW", "VIC", "",
]

COUNTRIES = [
    "USA", "Canada", "UK", "France", "Germany", "Australia", "Brazil",
    "Japan", "India", "Italy", "Spain", "Netherlands", "Sweden", "Norway",
]

STREETS = [
    "Main St", "Oak Ave", "Maple Dr", "Cedar Ln", "Pine Rd", "Elm St",
    "Washington Ave", "Park Blvd", "Lake Dr", "Hill Rd", "River Way",
    "Forest Ave", "Spring St", "Valley Rd", "Sunset Blvd", "Broadway",
    "Church St", "Market St", "High St", "School Rd",
]

COMPANIES = [
    "Acme Corp", "Globex", "Initech", "Umbrella Corp", "Stark Industries",
    "Wayne Enterprises", "Cyberdyne", "Soylent Corp", "Oscorp", "LexCorp",
    "Aperture Science", "Black Mesa", "Massive Dynamic", "Tyrell Corp",
    "Weyland-Yutani", "InGen", "Dharma Initiative", "Hooli", "Pied Piper",
    "Dunder Mifflin", "", "", "", "", "",  # many customers have no company
]

ARTIST_NAMES = [
    "AC/DC", "Accept", "Aerosmith", "Alanis Morissette", "Alice In Chains",
    "Antonio Carlos Jobim", "Apocalyptica", "Audioslave", "BackBeat",
    "Billy Cobham", "Black Label Society", "Black Sabbath", "Body Count",
    "Bruce Dickinson", "Buddy Guy", "Caetano Veloso", "Chico Buarque",
    "Chico Science", "Cidade Negra", "Claudio Zoli", "Creedence Clearwater Revival",
    "David Coverdale", "Deep Purple", "Def Leppard", "Dennis Chambers",
    "Djavan", "Dread Zeppelin", "Ed Motta", "Elis Regina", "Eric Clapton",
    "Faith No More", "Falamansa", "Foo Fighters", "Frank Sinatra",
    "Frank Zappa", "Funk Como Le Gusta", "Gene Krupa", "Gilberto Gil",
    "Gonzaguinha", "Green Day", "Guns N' Roses", "Incognito", "Iron Maiden",
    "James Brown", "Jamiroquai", "Jimi Hendrix", "Joe Satriani", "Jorge Ben",
    "Jota Quest", "Led Zeppelin", "Legiao Urbana", "Lenny Kravitz",
    "Los Hermanos", "Marillion", "Marisa Monte", "Marvin Gaye", "Metallica",
    "Miles Davis", "Milton Nascimento", "Muse", "Nirvana", "O Rappa",
    "O Terco", "Olodum", "Os Mutantes", "Os Paralamas Do Sucesso", "Ozzy Osbourne",
    "Page & Plant", "Pearl Jam", "Pink Floyd", "Planet Hemp", "Queen",
    "R.E.M.", "Raul Seixas", "Red Hot Chili Peppers", "Rush", "Santana",
    "Scorpions", "Skank", "Smashing Pumpkins", "Soundgarden", "Spyro Gyra",
    "Stevie Ray Vaughan", "Stone Temple Pilots", "System Of A Down",
    "Terry Bozzio", "The Black Crowes", "The Clash", "The Cult", "The Doors",
    "The Police", "The Rolling Stones", "The Smiths", "The Who", "Tim Maia",
    "Titas", "Tool", "U2", "UB40", "Van Halen", "Various Artists",
    "Velvet Revolver", "Whitesnake", "Zeca Pagodinho",
]

GENRES = [
    "Rock", "Jazz", "Metal", "Alternative & Punk", "Rock And Roll",
    "Blues", "Latin", "Reggae", "Pop", "Soundtrack", "Bossa Nova",
    "Easy Listening", "Heavy Metal", "R&B/Soul", "Electronica/Dance",
    "World", "Hip Hop/Rap", "Science Fiction", "TV Shows", "Sci Fi & Fantasy",
    "Drama", "Comedy", "Alternative", "Classical", "Opera",
]

MEDIA_TYPES = [
    "MPEG audio file",
    "Protected AAC audio file",
    "Protected MPEG-4 video file",
    "Purchased AAC audio file",
    "AAC audio file",
]

ALBUM_WORDS = [
    "Greatest", "Hits", "Live", "Unplugged", "Remastered", "Collection",
    "Best", "Volume", "Sessions", "Chronicles", "Anthology", "Classic",
    "Ultimate", "Essential", "Complete", "Definitive", "Gold", "Platinum",
    "Diamond", "Legacy", "Archive", "Masters", "Legends", "Acoustic",
    "Electric", "Underground", "Loaded", "Restless", "Facelift", "Nevermind",
    "Appetite", "Destruction", "Black Album", "Dark Side", "The Wall",
    "Back In Black", "Hysteria", "Paranoid", "Master Of Puppets", "Rust In Peace",
]

TRACK_WORDS = [
    "Love", "Fire", "Night", "Rain", "Sun", "Moon", "Star", "Road", "River",
    "Mountain", "Dream", "Thunder", "Storm", "Wind", "Shadow", "Light",
    "Dark", "Blues", "Rock", "Roll", "Groove", "Rhythm", "Soul", "Heart",
    "Mind", "Spirit", "Freedom", "Rebel", "Angel", "Devil", "God", "King",
    "Queen", "Prince", "Warrior", "Hunter", "Child", "Woman", "Man",
    "Baby", "Honey", "Sugar", "Sweet", "Bitter", "Wild", "Crazy", "Easy",
]

COMPOSERS = [
    "Angus Young, Malcolm Young, Brian Johnson",
    "Steven Tyler, Joe Perry",
    "Ozzy Osbourne, Tony Iommi, Geezer Butler, Bill Ward",
    "Robert Plant, Jimmy Page",
    "Freddie Mercury",
    "Kurt Cobain",
    "Eddie Vedder",
    "James Hetfield, Lars Ulrich",
    "Dave Grohl, Nate Mendel, Pat Smear",
    "Bono, The Edge, Adam Clayton, Larry Mullen",
    "Mick Jagger, Keith Richards",
    "Roger Waters",
    "Pete Townshend",
    "Eric Clapton",
    "Jimi Hendrix",
    "B.B. King",
    "Stevie Ray Vaughan",
    "Antonio Carlos Jobim",
    "Chico Buarque",
    "Caetano Veloso",
    "",  # some tracks have no composer
    "",
    "",
]

EMPLOYEE_TITLES = [
    "General Manager", "Sales Manager", "Sales Support Agent",
    "Sales Support Agent", "Sales Support Agent", "IT Manager",
    "IT Staff", "IT Staff",
]

PLAYLIST_NAMES = [
    "Music", "Movies", "TV Shows", "Audiobooks", "90s Music", "Audiobooks",
    "Music Videos", "Brazilian Music", "Classical", "Classical 101 - Deep Cuts",
    "Classical 101 - Next Steps", "Classical 101 - The Basics", "Grunge",
    "Heavy Metal Classic", "On-The-Go 1", "Rock", "Rock Classics", "Mega Rock",
]


def rand_phone():
    return f"+{random.randint(1,99)} ({random.randint(100,999)}) {random.randint(100,999)}-{random.randint(1000,9999)}"


def rand_postal():
    return f"{random.randint(10000,99999)}"


def rand_email(first, last):
    domains = ["gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "mail.com"]
    return f"{first.lower()}.{last.lower()}@{random.choice(domains)}"


def rand_address():
    return f"{random.randint(1,9999)} {random.choice(STREETS)}"


# ============ Generate tables ============
print("Generating Chinook benchmark data...")

# 1. ARTIST (275 rows)
N_ARTISTS = 275
artist_rows = []
used_names = set()
for i in range(1, N_ARTISTS + 1):
    if i <= len(ARTIST_NAMES):
        name = ARTIST_NAMES[i - 1]
    else:
        name = f"Artist {i}"
    artist_rows.append([i, name])
write_csv("asm_artist.csv", ["artist_id", "name"], artist_rows)

# 2. ALBUM (347 rows)
N_ALBUMS = 347
album_rows = []
for i in range(1, N_ALBUMS + 1):
    w1 = random.choice(ALBUM_WORDS)
    w2 = random.choice(ALBUM_WORDS)
    title = f"{w1} {w2}" if random.random() > 0.3 else w1
    if random.random() > 0.5:
        title += f" Vol. {random.randint(1, 5)}"
    artist_id = random.randint(1, N_ARTISTS)
    album_rows.append([i, title, artist_id])
write_csv("asm_album.csv", ["album_id", "title", "artist_id"], album_rows)

# 3. MEDIA_TYPE (5 rows)
mt_rows = [[i + 1, MEDIA_TYPES[i]] for i in range(len(MEDIA_TYPES))]
write_csv("asm_media_type.csv", ["media_type_id", "name"], mt_rows)

# 4. GENRE (25 rows)
genre_rows = [[i + 1, GENRES[i]] for i in range(len(GENRES))]
write_csv("asm_genre.csv", ["genre_id", "name"], genre_rows)

# 5. TRACK (3503 rows)
N_TRACKS = 3503
track_rows = []
for i in range(1, N_TRACKS + 1):
    w1 = random.choice(TRACK_WORDS)
    w2 = random.choice(TRACK_WORDS)
    name = f"{w1} {w2}" if random.random() > 0.4 else f"The {w1}"
    album_id = random.randint(1, N_ALBUMS)
    media_type_id = random.randint(1, len(MEDIA_TYPES))
    genre_id = random.randint(1, len(GENRES))
    composer = random.choice(COMPOSERS)
    milliseconds = random.randint(120000, 600000)
    nbytes = int(milliseconds * random.uniform(8.0, 12.0))
    unit_price = random.choice([0.99, 1.29, 1.99])
    track_rows.append([i, name, album_id, media_type_id, genre_id, composer,
                       milliseconds, nbytes, unit_price])
write_csv("asm_track.csv",
          ["track_id", "name", "album_id", "media_type_id", "genre_id",
           "composer", "milliseconds", "bytes", "unit_price"],
          track_rows)

# 6. PLAYLIST (18 rows)
playlist_rows = [[i + 1, PLAYLIST_NAMES[i]] for i in range(len(PLAYLIST_NAMES))]
write_csv("asm_playlist.csv", ["playlist_id", "name"], playlist_rows)

# 7. PLAYLIST_TRACK (composite PK: playlist_id, track_id) - ~8715 rows
pt_set = set()
for pid in range(1, len(PLAYLIST_NAMES) + 1):
    n_tracks = random.randint(50, 800)
    chosen = random.sample(range(1, N_TRACKS + 1), min(n_tracks, N_TRACKS))
    for tid in chosen:
        pt_set.add((pid, tid))
pt_rows = sorted(pt_set)
write_csv("asm_playlist_track.csv", ["playlist_id", "track_id"], pt_rows)

# 8. EMPLOYEE (8 rows, self-referencing FK)
N_EMPLOYEES = 8
emp_rows = []
for i in range(1, N_EMPLOYEES + 1):
    last = random.choice(LAST_NAMES)
    first = random.choice(FIRST_NAMES)
    title = EMPLOYEE_TITLES[i - 1] if i <= len(EMPLOYEE_TITLES) else "Staff"
    reports_to = "" if i == 1 else random.randint(1, max(1, i - 1))
    bd = rand_date(date(1960, 1, 1), date(1985, 12, 31)).isoformat()
    hd = rand_date(date(2002, 1, 1), date(2010, 12, 31)).isoformat()
    addr = rand_address()
    city = random.choice(CITIES)
    state = random.choice(STATES)
    country = random.choice(COUNTRIES)
    postal = rand_postal()
    phone = rand_phone()
    fax = rand_phone()
    email = rand_email(first, last)
    emp_rows.append([i, last, first, title, reports_to, bd, hd,
                     addr, city, state, country, postal, phone, fax, email])
write_csv("asm_employee.csv",
          ["employee_id", "last_name", "first_name", "title", "reports_to",
           "birth_date", "hire_date", "address", "city", "state", "country",
           "postal_code", "phone", "fax", "email"],
          emp_rows)

# 9. CUSTOMER (59 rows)
N_CUSTOMERS = 59
cust_rows = []
# support_rep_id must reference employee - pick from sales agents (IDs 3-5 typically)
sales_reps = [i for i in range(1, N_EMPLOYEES + 1)
              if i <= len(EMPLOYEE_TITLES) and "Sales Support" in EMPLOYEE_TITLES[i - 1]]
if not sales_reps:
    sales_reps = list(range(1, N_EMPLOYEES + 1))

for i in range(1, N_CUSTOMERS + 1):
    first = random.choice(FIRST_NAMES)
    last = random.choice(LAST_NAMES)
    company = random.choice(COMPANIES)
    addr = rand_address()
    city = random.choice(CITIES)
    state = random.choice(STATES)
    country = random.choice(COUNTRIES)
    postal = rand_postal()
    phone = rand_phone()
    fax = rand_phone() if random.random() > 0.3 else ""
    email = rand_email(first, last)
    support_rep_id = random.choice(sales_reps)
    cust_rows.append([i, first, last, company, addr, city, state, country,
                      postal, phone, fax, email, support_rep_id])
write_csv("asm_customer.csv",
          ["customer_id", "first_name", "last_name", "company", "address",
           "city", "state", "country", "postal_code", "phone", "fax",
           "email", "support_rep_id"],
          cust_rows)

# 10. INVOICE (412 rows)
N_INVOICES = 412
inv_rows = []
for i in range(1, N_INVOICES + 1):
    cid = random.randint(1, N_CUSTOMERS)
    inv_date = rand_date(date(2009, 1, 1), date(2013, 12, 31)).isoformat()
    # Get customer's address info
    c = cust_rows[cid - 1]
    addr = c[4]
    city = c[5]
    state = c[6]
    country = c[7]
    postal = c[8]
    total = round(random.uniform(0.99, 25.86), 2)
    inv_rows.append([i, cid, inv_date, addr, city, state, country, postal, total])
write_csv("asm_invoice.csv",
          ["invoice_id", "customer_id", "invoice_date", "billing_address",
           "billing_city", "billing_state", "billing_country",
           "billing_postal_code", "total"],
          inv_rows)

# 11. INVOICE_LINE (2240 rows)
N_LINES = 2240
line_rows = []
for i in range(1, N_LINES + 1):
    inv_id = random.randint(1, N_INVOICES)
    tid = random.randint(1, N_TRACKS)
    up = random.choice([0.99, 1.29, 1.99])
    qty = random.randint(1, 3)
    line_rows.append([i, inv_id, tid, up, qty])
write_csv("asm_invoice_line.csv",
          ["invoice_line_id", "invoice_id", "track_id", "unit_price", "quantity"],
          line_rows)

print("\nDone! Generated 11 tables for Chinook benchmark.")
