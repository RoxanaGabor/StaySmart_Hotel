import xml.etree.ElementTree as ET

def update_notes(existing_xml: str, new_notes: str) -> str:
    new_notes = (new_notes or "").strip()
    if not new_notes:
        raise ValueError("Notes cannot be empty")

    try:
        if existing_xml and existing_xml.strip():
            root = ET.fromstring(existing_xml)
        else:
            root = ET.Element("preferences")
    except ET.ParseError:
        root = ET.Element("preferences")

    if root.tag != "preferences":
        wrapper = ET.Element("preferences")
        wrapper.append(root)
        root = wrapper

    notes_el = root.find("notes")
    if notes_el is None:
        notes_el = ET.SubElement(root, "notes")

    notes_el.text = new_notes
    return ET.tostring(root, encoding="unicode")
