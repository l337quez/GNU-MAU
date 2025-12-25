def image_to_bytes(image_path, output_py_file):
    with open(image_path, "rb") as f:
        image_data = f.read()
    
    with open(output_py_file, "w") as f:
        f.write("icon = bytes([\n")
        for i, byte in enumerate(image_data):
            f.write(f"0x{byte:02X}, ")
            if (i + 1) % 16 == 0:
                f.write("\n")
        f.write("\n])")
    
    print(f"¡Listo! Archivo '{output_py_file}' generado correctamente.")

# Uso: pon el nombre de tu imagen aquí
image_to_bytes("assets/banner/mau-logo-alpha.png", "icon.py")