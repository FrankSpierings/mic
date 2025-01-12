from mic.mendix_client import MendixClient
from mic.helper import pretty_print_objects
from prompt_toolkit import HTML, prompt, print_formatted_text
from prompt_toolkit.history import InMemoryHistory
from html import escape
import argparse
from os import path
import traceback


def print_help():
    txt = """
commands:
    help                    Print this help
    !                       Find all the klasses
    ?                       Print 1 object of each klass
    //<klass> [nr] [offset] Find nr (default=1) of objects of the given klass: //System.User
    <guid>                  Find the object with the given guid: 281475001951441
    +<guid> <name> <value> Update attribute (name) for the given object
    login [<username>]      Login with the given username, or login as anonymous
    @<guid>                 Login as each defined user and check access to object
    $<guid>                 Download file with guid
"""
    print(txt)

def repl(client: MendixClient, downloads, credentials=None):
    history = InMemoryHistory()
    while True:
        try:
            instruction = prompt(
                HTML(
                    f"<style fg='ansiblue'>[{escape(client.current_user)}</style> @ <style fg='ansigreen'>{escape(client.base_url)}]: </style>"
                ),
                history=history
            )

            if instruction == "" or instruction == "help":
                print_help()

            # Retrieve 10 objects of class type input starts with //
            elif instruction.startswith("//"):
                # If the input contains a space and a digit, acquire that many objects
                splits = instruction.split(" ")
                results = []
                klass = ''
                if len(splits) > 1 and splits[1].isdigit():
                    offset = 0
                    if len(splits) > 2 and splits[2].isdigit():
                        offset = splits[2]
                    klass = splits[0][2:]
                    results = client.get_objects_by_klass(klass, splits[1], offset=offset)
                else:
                    klass = instruction[2:]
                    results = client.get_objects_by_klass(klass, 1)
                if len(results) > 0:
                    pretty_print_objects(results)
                else:
                    print_formatted_text(
                        HTML(f'<style fg="ansiyellow">[No results for {escape(klass)}]</style>')
                    )

            # Retrieve 1 object by its guid/id, if input is a number
            elif instruction.isdigit():
                results = client.get_object_by_id(instruction)
                if len(results) > 0:
                    pretty_print_objects(results)
                else:
                    print_formatted_text(
                        HTML(
                            f'<style fg="ansiyellow">[No results for {escape(instruction)}]</style>'
                        )
                    )

            # Retrieve all object klass types if input is !
            elif instruction == "!":
                for klass in sorted(client.get_klasses()):
                    print(f"//{klass}")

            # Retrieve 1 object for each class type if input is ?
            elif instruction == "?":    
                for klass in sorted(client.get_klasses()):
                    results = client.get_objects_by_klass(klass, 1)
                    if len(results) > 0:
                        pretty_print_objects(results)
                    else:
                        print_formatted_text(
                            HTML(
                                f'<style fg="ansiyellow">[No results for {escape(klass)}]</style>'
                            )
                        )

            # Retrieve all object class types if input is list
            elif instruction == "list":
                for klass in client.get_klasses():
                    print(f"//{klass}")

            # Login as different (or anonymous) user, if input is 'login username' (or 'login')
            elif instruction.startswith("login"):
                splits = instruction.split(" ")
                if len(splits) > 1:
                    username = splits[1]
                    if username in [i[0] for i in credentials]:
                        password = [i[1] for i in credentials if i[0] == username][0]
                        print(f"Logging in as {username}")
                        try:
                            client.login(username, password)
                        except RuntimeError:
                            print(
                                f"Login failed for {username}"
                            )
                    else:
                        print("User not found")
                else:
                    print(f"Logging in as anonymous")
                    client.login()

            # Update an attribute of an object using: '+<guid> <attribute name> <value>'
            elif instruction.startswith("+"):
                splits = instruction[1:].split(" ")
                if len(splits) >= 3 and splits[0].isdigit():
                    guid = splits[0]
                    name = splits[1]
                    value = " ".join(splits[2:])
                    results = client.update_object_attribute(guid, name, value)
                    if len(results) > 0:
                        pretty_print_objects(results)
                    else:
                        print_formatted_text(
                            HTML(
                                f'<style fg="ansiyellow">[No results for {escape(instruction)}]</style>'
                            )
                        )

            # Check object for all users: @<guid>
            elif instruction.startswith("@"):
                if instruction[1:].isdigit():
                    guid = instruction[1:]
                    current_user = client.current_user
                    for username in [i[0] for i in credentials]:
                        password = [i[1] for i in credentials if i[0] == username][0]
                        print(f'Login as {username}')
                        client.login(username, password)
                        results = client.get_object_by_id(instruction)
                        if len(results) > 0:
                            pretty_print_objects(results)
                        else:
                            print_formatted_text(
                                HTML(
                                    f'<style fg="ansiyellow">[No results for {escape(instruction)}]</style>'
                                )
                            )
                    # Log back in as the current user
                    if current_user.startswith('Anonymous'):
                        client.login()
                    else:
                        password = [i[1] for i in credentials if i[0] == username][0]
                        client.login(current_user, password)

            # Download file: $<guid>
            elif instruction.startswith("$"):
                if instruction[1:].isdigit():
                    guid = instruction[1:]
                    result = client.get_object_by_id(guid)
                    name = result[0].get('attributes').get('Name', {}).get('value')
                    client.download_file(guid, name, downloads)

        except KeyboardInterrupt:
            print('Exit...')
            return
        except Exception:
            traceback.print_exc()
            continue

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--credentials-file",
        "-c",
        type=argparse.FileType('r'),
        help="Path to username:password file",
    )
    parser.add_argument("--proxy", "-p", help="Http(s) proxy: 127.0.0.1:8080")
    parser.add_argument("--insecure", "-k", help="Disable TLS certificate verification", action='store_false')
    parser.add_argument("--download-path", "-d", help="Downloads destination path", default='./')
    parser.add_argument(
        "base_url", help="The URL to operate on: https://example.mendixcloud.com"
    )
    args = parser.parse_args()
    credentials = None
    if args.credentials_file:
        credentials = [i.split(':', 1) for i in args.credentials_file.read().split('\n')]

    if not path.exists(args.download_path):
        print(f'Download path not found: {args.download_path}')
        parser.print_help()
        return

    client = MendixClient(base_url=args.base_url.rstrip('/'), proxy=args.proxy, verify=args.insecure)
    repl(client, args.download_path, credentials)

if __name__ == "__main__":
    main()
