from prompt_toolkit import HTML, print_formatted_text
from html import escape

def pretty_format_objects(objects):
    output = ''
    for obj in objects:
        if output != "":
            output += "\n"
        # print klass
        output += f'<style fg="ansiblue">[{escape(obj["objectType"])}]</style> @ <style fg="ansicyan">{escape(obj["guid"])}</style>'
        # append guid
        attributes = obj.get("attributes", {})
        for attribute in attributes.items(): 
            output += "\n\t"
            if attribute[1].get("readonly", False):                
                output += f'<style fg="ansigreen">{escape(attribute[0])}</style>'
            else:
                output += f'<style fg="ansired">{escape(attribute[0])}</style>'
            output += ": " + escape(str(attribute[1].get("value", "")))
    return HTML(output)


def pretty_print_objects(objects):
    print_formatted_text(pretty_format_objects(objects))
