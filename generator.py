import shutil
import zipfile
from pathlib import Path
import json
import re

import hashlib
import subprocess


def generate_namespace(artist, album):

    source = (
        f"{artist.strip().lower()}"
        f"+{album.strip().lower()}"
    )

    digest = hashlib.sha256(
        source.encode("utf-8")
    ).hexdigest()

    return f"df_{digest[:8]}"

ROOT = Path(__file__).parent

CONFIG = ROOT / "config.json"

with open(CONFIG, "r", encoding="utf-8") as file:
    config = json.load(file)

NAMESPACE = generate_namespace(
    config["album"]["artist"],
    config["album"]["name"]
)

if not re.fullmatch(
        r"df_[a-f0-9]{8}",
        NAMESPACE
):
    raise ValueError(
        f'Config error: generated namespace is invalid: "{NAMESPACE}"'
    )

if not re.fullmatch(
        r"df_[a-f0-9]{8}",
        NAMESPACE
):
    raise ValueError(
        f'Config error: generated namespace is invalid: "{NAMESPACE}"'
    )

TEMPLATE = (
    ROOT
    / "templates"
    / "neoforge"
    / "template-1.21.1.zip"
)
OUTPUT = ROOT / "output"

SRC = (
    OUTPUT
    / "src"
    / "main"
)

JAVA = SRC / "java"

RESOURCES = SRC / "resources"

ASSETS = (
    RESOURCES
    / "assets"
    / NAMESPACE
)

DATA = (
    RESOURCES
    / "data"
    / NAMESPACE
)

if OUTPUT.exists():
    shutil.rmtree(OUTPUT)

OUTPUT.mkdir()


print("Extracting template...")

with zipfile.ZipFile(TEMPLATE, "r") as zip_file:
    zip_file.extractall(OUTPUT)

print("Done!")
print()
print("Configuration:")
print("-------------------------")
print("Namespace:", NAMESPACE)
print("Version:", config["version"])
print("Album  :", config["album"]["name"])
print("Artist :", config["album"]["artist"])
print()

print("Songs:")

for song in config["songs"]:
    print(f" - {song['title']}")







def song_id(title: str) -> str:

    return re.sub(
        r"[^a-z0-9]+",
        "_",
        title.lower()
    ).strip("_")




def write_file(path: Path, contents: str):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    path.write_text(
        contents,
        encoding="utf-8"
    )


def read_template(name: str) -> str:

    template = (
        ROOT
        / "templates"
        / "shared"
        / name
    )

    return template.read_text(
        encoding="utf-8"
    )


def write_json(path: Path, data):

    path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with open(
            path,
            "w",
            encoding="utf-8"
    ) as file:

        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False
        )


def generate_gradle_properties():

    print("Generating gradle.properties...")

    gradle_properties = OUTPUT / "gradle.properties"

    contents = gradle_properties.read_text(
        encoding="utf-8"
    )

    contents = contents.replace(
        "mod_id=dftemplate",
        f"mod_id={NAMESPACE}"
    )

    mod_name = (
        f"DF | {config['album']['artist']} - "
        f"{config['album']['name']}"
    )

    contents = contents.replace(
        "mod_name=DF Template",
        f"mod_name={mod_name}"
    )

    contents = contents.replace(
        "mod_group_id=com.discforge.template",
        "mod_group_id=com.discforge.generated"
    )

    gradle_properties.write_text(
        contents,
        encoding="utf-8"
    )


def generate_album_info():

    print("Generating AlbumInfo.java...")

    album_info = (
            JAVA
            / "com"
            / "discforge"
            / "generated"
            / NAMESPACE
            / "album"
            / "AlbumInfo.java"
    )

    template = read_template(
        "AlbumInfo.java.template"
    )

    template = template.replace(
        "com.discforge.template",
        f"com.discforge.generated.{NAMESPACE}"
    )

    template = template.replace(
        "{{ALBUM_ID}}",
        config["album"]["id"]
    )

    template = template.replace(
        "{{MOD_ID}}",
        NAMESPACE
    )

    template = template.replace(
        "{{ALBUM_NAME}}",
        config["album"]["name"]
    )

    template = template.replace(
        "{{ARTIST}}",
        config["album"]["artist"]
    )

    songs = []

    for song in config["songs"]:
        song_identifier = song_id(song["title"])

        songs.append(
            f'''\
                            new SongInfo(
                                    "{song_identifier}",
                                    "{song["title"]}",
                                    "{config["album"]["id"]}",
                                    "{config["album"]["artist"]}",
                                    {song["length"]},
                                    {song["comparator"]}
                            )'''
        )

    template = template.replace(
        "{{SONGS}}",
        ",\n".join(songs)
    )

    write_file(
        album_info,
        template
    )


def replace_template_namespace():

    print("Replacing template namespace...")

    for path in OUTPUT.rglob("*"):

        if not path.is_file():
            continue

        try:
            contents = path.read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError:
            continue

        if "dftemplate" not in contents:
            continue

        contents = contents.replace(
            "dftemplate",
            NAMESPACE
        )

        path.write_text(
            contents,
            encoding="utf-8"
        )

def validate_config():

    print("Validating configuration...")

    album = config.get("album")
    songs = config.get("songs")

    version = config.get("version")

    if not version or not isinstance(version, str):
        raise ValueError(
            'Config error: "version" must be a non-empty string.'
        )

    if not isinstance(album, dict):
        raise ValueError(
            'Config error: "album" must be an object.'
        )

    if not isinstance(songs, list):
        raise ValueError(
            'Config error: "songs" must be a list.'
        )

    for field in ("id", "name", "artist", "cover"):
        if not album.get(field):
            raise ValueError(
                f'Config error: album "{field}" is missing.'
            )

    for field in ("id", "name", "artist"):
        if not isinstance(album[field], str) or not album[field].strip():
            raise ValueError(
                f'Config error: album "{field}" must be a non-empty string.'
            )

    if not re.fullmatch(
            r"[a-z0-9_]+",
            album["id"]
    ):
        raise ValueError(
            'Config error: album "id" must contain '
            'only lowercase letters, numbers, and underscores.'
        )

    if not songs:
        raise ValueError(
            'Config error: "songs" must contain at least one song.'
        )

    song_ids = set()

    for index, song in enumerate(songs, start=1):

        if not isinstance(song, dict):
            raise ValueError(
                f"Config error: song #{index} must be an object."
            )

        for field in (
            "title",
            "file",
            "length",
            "comparator"
        ):
            if field not in song:
                raise ValueError(
                    f'Config error: song #{index} '
                    f'is missing "{field}".'
                )

        cover = ROOT / "input" / album["cover"]

        if not cover.is_file():
            raise ValueError(
                f'Config error: album cover does not exist: "{cover}"'
            )

        if not song["title"].strip():
            raise ValueError(
                f"Config error: song #{index} has an empty title."
            )

        if not song["file"].strip():
            raise ValueError(
                f"Config error: song #{index} has an empty file."
            )

        source = ROOT / "input" / song["file"]

        if not source.is_file():
            raise ValueError(
                f'Config error: audio file for song #{index} '
                f'does not exist: "{source}"'
            )

        if not isinstance(song["length"], int):
            raise ValueError(
                f'Config error: song #{index} '
                '"length" must be an integer.'
            )

        if song["length"] <= 0:
            raise ValueError(
                f'Config error: song #{index} '
                '"length" must be greater than 0.'
            )

        if not isinstance(song["comparator"], int):
            raise ValueError(
                f'Config error: song #{index} '
                '"comparator" must be an integer.'
            )

        if not 0 <= song["comparator"] <= 15:
            raise ValueError(
                f'Config error: song #{index} '
                '"comparator" must be between 0 and 15.'
            )

        identifier = song_id(song["title"])

        if not identifier:
            raise ValueError(
                f'Config error: song #{index} '
                f'has an invalid title: "{song["title"]}".'
            )

        if identifier in song_ids:
            raise ValueError(
                f'Config error: song #{index} '
                f'has a duplicate ID: "{identifier}".'
            )

        song_ids.add(identifier)

    print("Configuration valid.")

def generate_java_sources():

    print("Generating Java sources...")

    old_package = "com.discforge.template"
    new_package = f"com.discforge.generated.{NAMESPACE}"

    for path in (
        OUTPUT
        / "src"
        / "main"
        / "java"
    ).rglob("*.java"):

        contents = path.read_text(
            encoding="utf-8"
        )

        contents = contents.replace(
            old_package,
            new_package
        )

        contents = contents.replace(
            '"dftemplate"',
            f'"{NAMESPACE}"'
        )

        contents = contents.replace(
            "album.dftemplate.",
            f"album.{NAMESPACE}."
        )

        contents = contents.replace(
            "artist.dftemplate.",
            f"artist.{NAMESPACE}."
        )

        path.write_text(
            contents,
            encoding="utf-8"
        )

def relocate_java_package():

    print("Relocating Java package...")

    old_path = (
        JAVA
        / "com"
        / "discforge"
        / "template"
    )

    new_path = (
        JAVA
        / "com"
        / "discforge"
        / "generated"
        / NAMESPACE
    )

    new_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    shutil.move(
        str(old_path),
        str(new_path)
    )

    template_path = (
        JAVA
        / "com"
        / "discforge"
    )

    if template_path.exists():
        try:
            template_path.rmdir()
        except OSError:
            pass


def for_each_song(callback):

    for song in config["songs"]:

        callback(
            song,
            song_id(song["title"])
        )


def generate_album_json():

    print("Generating album.json...")

    album_json = {
        "modid": NAMESPACE,
        "id": config["album"]["id"],
        "name": config["album"]["name"],
        "artist": config["album"]["artist"],
        "songs": [
            {
                "id": song_id(song["title"]),
                "title": song["title"]
            }
            for song in config["songs"]
        ]
    }

    write_json(
        DATA
        / "discforge"
        / "album.json",
        album_json
    )


def generate_sounds_json():

    print("Generating sounds.json...")

    sounds = {}

    for song in config["songs"]:

        identifier = song_id(song["title"])

        sounds[identifier] = {
            "sounds": [
                {
                    "name": f"{NAMESPACE}:{identifier}",
                    "stream": True
                }
            ]
        }

    write_json(
        OUTPUT
        / "src"
        / "main"
        / "resources"
        / "assets"
        / f"{NAMESPACE}"
        / "sounds.json",
        sounds
    )



def generate_audio_files():

    print("Copying audio files...")

    for song in config["songs"]:

        identifier = song_id(song["title"])

        source = ROOT / "input" / song["file"]

        destination = (
            ASSETS
            / "sounds"
            / f"{identifier}.ogg"
        )

        destination.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        shutil.copy2(
            source,
            destination
        )


def generate_cover():

    print("Copying album cover...")

    source = ROOT / "input" / config["album"]["cover"]

    destination = (
        ASSETS
        / "textures"
        / "item"
        / "disc.png"
    )

    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    shutil.copy2(
        source,
        destination
    )


def generate_jukebox_songs():

    print("Generating jukebox songs...")

    for song in config["songs"]:

        identifier = song_id(song["title"])

        jukebox_song = {
            "sound_event": {
                "sound_id": f"{NAMESPACE}:{identifier}"
            },
            "description": {
                "translate": f"jukebox_song.{NAMESPACE}.{identifier}"
            },
            "length_in_seconds": song["length"],
            "comparator_output": song["comparator"]
        }

        write_json(
            DATA
            / "jukebox_song"
            / f"{identifier}.json",
            jukebox_song
        )

def generate_item_models():

    print("Generating item models...")

    def generate_model(song, identifier):

        model = {
            "parent": "minecraft:item/generated",
            "textures": {
                "layer0": f"{NAMESPACE}:item/disc"
            }
        }

        write_json(
            ASSETS
            / "models"
            / "item"
            / f"{identifier}_disc.json",
            model
        )

    for_each_song(generate_model)


def generate_item_definitions():

    print("Generating item definitions...")

    def generate_item(song, identifier):

        item = {
            "model": {
                "type": "minecraft:model",
                "model": f"{NAMESPACE}:item/{identifier}_disc"
            }
        }

        write_json(
            ASSETS
            / "items"
            / f"{identifier}_disc.json",
            item
        )

    for_each_song(generate_item)


def generate_language_file():

    print("Generating en_us.json...")

    language = {}

    for song in config["songs"]:

        identifier = song_id(song["title"])

        language[
            f"item.{NAMESPACE}.{identifier}_disc"
        ] = song["title"]

        language[
            f"jukebox_song.{NAMESPACE}.{identifier}"
        ] = song["title"]

    language[
        f"album.{NAMESPACE}.{config['album']['id']}"
    ] = config["album"]["name"]

    language[
        f"artist.{NAMESPACE}.{config['album']['artist']}"
    ] = config["album"]["artist"]

    write_json(
        ASSETS
        / "lang"
        / "en_us.json",
        language
    )

def verify_no_template_namespace():

    print("Checking for leftover dftemplate references...")

    leftovers = []

    for path in OUTPUT.rglob("*"):

        if not path.is_file():
            continue

        try:
            contents = path.read_text(
                encoding="utf-8"
            )
        except UnicodeDecodeError:
            continue

        if "dftemplate" in contents:
            leftovers.append(path)

    if leftovers:

        print()
        print("ERROR: Found leftover dftemplate references:")

        for path in leftovers:
            print(f" - {path}")

        raise RuntimeError(
            "Template namespace was not fully replaced."
        )

    print("No leftover dftemplate references found.")


def build_mod():

    print()
    print("Building mod...")
    print("-------------------------")

    result = subprocess.run(
        ["cmd", "/c", "gradlew.bat", "build"],
        cwd=OUTPUT,
        check=False
    )

    if result.returncode != 0:
        print()
        print("Build failed.")
        raise SystemExit(1)

    print()
    print("Build successful!")


def package_mod():

    print()
    print("Packaging mod...")
    print("-------------------------")

    libs = OUTPUT / "build" / "libs"

    jars = [
        path
        for path in libs.glob("*.jar")
        if "-sources" not in path.name
    ]

    if len(jars) != 1:
        print()
        print(
            f"Packaging failed: expected exactly one mod JAR, "
            f"found {len(jars)}."
        )
        raise SystemExit(1)

    source = jars[0]

    artist_id = re.sub(
        r"[^a-z0-9]+",
        "_",
        config["album"]["artist"].lower()
    ).strip("_")

    artist_id = artist_id[0]

    album_id = config["album"]["id"]

    output_name = (
        f"df_{artist_id}_{album_id}"
        f"-{config['version']}.jar"
    )

    destination = OUTPUT / "build" / output_name

    shutil.move(
        str(source),
        str(destination)
    )

    print(f"Created: {destination.name}")

    return destination


def clean_output(final_jar):

    print()
    print("Cleaning output...")
    print("-------------------------")

    build_dir = OUTPUT / "build"

    if not final_jar.exists():
        raise RuntimeError(
            "Final JAR does not exist; refusing to clean output."
        )

    for path in OUTPUT.iterdir():

        if path == build_dir:
            continue

        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    for path in build_dir.iterdir():

        if path == final_jar:
            continue

        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    print("Cleanup complete.")
    print(f"Final JAR: {final_jar}")


try:
    validate_config()
except ValueError as error:
    print()
    print("Configuration error:")
    print(error)
    raise SystemExit(1)

generate_gradle_properties()

generate_java_sources()
relocate_java_package()

generate_album_info()

replace_template_namespace()

generate_album_json()
generate_sounds_json()
generate_audio_files()
generate_cover()
generate_jukebox_songs()
generate_item_models()
generate_item_definitions()
generate_language_file()

verify_no_template_namespace()

build_mod()

final_jar = package_mod()

clean_output(final_jar)