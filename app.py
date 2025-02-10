import streamlit as st
import requests
import base64
import json
from PIL import Image
import io
from pillow_heif import register_heif_opener
import os
import tempfile
import hashlib
import random
import matplotlib.image as mpimg
import numpy as np

# Registrar el soporte para archivos HEIC
register_heif_opener()

# Configuración de la página
st.set_page_config(
    page_title="Moneda AI - Procesador de Facturas",
    page_icon="🧾",
    layout="wide"
)

# Modificar estilos CSS para centrar contenido
st.markdown("""
    <style>
        .main {
            padding: 2rem;
        }
        .stButton>button {
            width: 50%;
            background-color: #4CAF50;
            color: white;
            margin: 0 auto;
            display: block;
        }
        .upload-section {
            text-align: center;
            max-width: 800px;
            margin: 0 auto;
        }
        .results-section {
            max-width: 800px;
            margin: 2rem auto;
        }
    </style>
""", unsafe_allow_html=True)

# Sidebar para configuración
st.sidebar.title("⚙️ Configuración")
base_url = st.sidebar.text_input(
    "Base URL",
    value="https://moneda-ai-backend-dev-727974179685.us-central1.run.app",
    help="URL del servidor backend"
)
password_input = st.sidebar.text_input("Password", type="password")

# Validación de contraseña
if password_input:
    if password_input != st.secrets["PASSWORD"]:
        st.error("🔒 Contraseña incorrecta. Por favor, verifica e intenta nuevamente.")
        st.stop()
else:
    st.warning("🔑 Ingresa la contraseña para acceder al sistema")
    st.stop()

# Contenido principal centrado
st.title("🧾 Procesador de Facturas")
st.markdown("---")

# Sección de carga de imagen centrada
st.markdown("<div class='upload-section'>", unsafe_allow_html=True)
st.markdown("### Imagen de Factura")
uploaded_file = st.file_uploader(
    "Formatos soportados: JPG, PNG, HEIC",
    type=["jpg", "png", "HEIC"]
)

def convertir_heic_a_jpg(ruta_archivo_heic, ruta_archivo_jpg):
    ruta_archivo_heic = os.path.normpath(ruta_archivo_heic)
    ruta_archivo_jpg = os.path.normpath(ruta_archivo_jpg)
    
    if not os.path.exists(ruta_archivo_heic):
        raise FileNotFoundError(f"No se encuentra el archivo: {ruta_archivo_heic}")
        
    imagen = Image.open(ruta_archivo_heic)
    imagen.save(ruta_archivo_jpg, "JPEG")

def process_image(uploaded_file):
    """Función auxiliar para procesar la imagen"""
    image_bytes = uploaded_file.read()
    
    # Abrir la imagen con PIL
    img = Image.open(io.BytesIO(image_bytes))
    
    # Convertir a RGB si es necesario
    if img.mode in ('RGBA', 'LA'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'RGBA':
            background.paste(img, mask=img.split()[3])
        else:
            background.paste(img, mask=img.split()[1])
        img = background
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    # Guardar en bytes
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='JPEG')
    image_bytes = img_byte_arr.getvalue()
    
    return image_bytes, np.array(img)

if uploaded_file:
    try:
        temp_files = []  # Lista para trackear archivos temporales
        
        if uploaded_file.type == "image/heic":
            # Generar hash único para el nombre del archivo
            random_num = random.randint(0, 1000)
            filename_hash = hashlib.md5(f"{uploaded_file.name}{random_num}".encode()).hexdigest()
            temp_heic_name = f"{uploaded_file.name.split('.')[0]}_{filename_hash}.heic"
            temp_jpg_name = f"{uploaded_file.name.split('.')[0]}_{filename_hash}.jpg"
            
            # Rutas temporales
            temp_heic_path = os.path.join(tempfile.gettempdir(), temp_heic_name)
            temp_jpg_path = os.path.join(tempfile.gettempdir(), temp_jpg_name)
            temp_files.extend([temp_heic_path, temp_jpg_path])
            
            # Guardar archivo HEIC
            with open(temp_heic_path, 'wb') as f:
                f.write(uploaded_file.getvalue())
            
            # Convertir HEIC a JPG de manera directa
            try:
                imagen = Image.open(temp_heic_path)
                imagen.save(temp_jpg_path, "JPEG")
                
                # Leer la imagen directamente con PIL en lugar de matplotlib
                with Image.open(temp_jpg_path) as img:
                    image_bytes = io.BytesIO()
                    img.save(image_bytes, format='JPEG')
                    image_bytes = image_bytes.getvalue()
            except Exception as e:
                st.error(f"Error en la conversión de imagen: {str(e)}")
                raise e
        else:
            # Procesar PNG, JPG y otros formatos
            image_bytes, image_array = process_image(uploaded_file)

        # Mostrar preview
        st.image(
            image_array,
            caption="Vista previa",
            use_container_width=True
        )
        
        if st.button("🔍 Procesar Factura"):
            with st.spinner('Procesando imagen...'):
                try:
                    base64_image = base64.b64encode(image_bytes).decode('utf-8')
                    payload = {
                        "base64_image": base64_image,
                        "user_id": 1
                    }
                    headers = {"Content-Type": "application/json"}
                    url = f"{base_url.rstrip('/')}/agent/process-receipt/"
                    print(f"URL: {url}")
                    response = requests.post(url, json=payload, headers=headers)
                    
                    if response.status_code == 200:
                        result = response.json()
                        response_data = result.get('response_data', {})
                        
                        st.markdown("<div class='results-section'>", unsafe_allow_html=True)
                        st.markdown(f"""
                        <div style='border: 2px solid #4CAF50; padding: 20px; border-radius: 8px; background-color: #f9f9f9;'>
                            <table style='width: 100%; border-collapse: collapse;'>
                                <tr>
                                    <td style='padding: 15px; border-bottom: 1px solid #ddd; width: 30%;'><strong>🏪 Comercio:</strong></td>
                                    <td style='padding: 15px; border-bottom: 1px solid #ddd;'>{response_data.get('vendor_name', 'N/A')}</td>
                                </tr>
                                <tr>
                                    <td style='padding: 15px; border-bottom: 1px solid #ddd;'><strong>🔢 ID Transacción:</strong></td>
                                    <td style='padding: 15px; border-bottom: 1px solid #ddd;'>{response_data.get('transaction_id', 'N/A')}</td>
                                </tr>
                                <tr>
                                    <td style='padding: 15px; border-bottom: 1px solid #ddd;'><strong>📅 Fecha/Hora:</strong></td>
                                    <td style='padding: 15px; border-bottom: 1px solid #ddd;'>{response_data.get('date_time', 'N/A')}</td>
                                </tr>
                                <tr>
                                    <td style='padding: 15px;'><strong>💰 Monto Total:</strong></td>
                                    <td style='padding: 15px;'>{response_data.get('currency', '')} {response_data.get('total_amount', 'N/A')}</td>
                                </tr>
                            </table>
                        </div>
                        </div>
                        """, unsafe_allow_html=True)
                    elif response.status_code == 422:
                        error_data = response.json()
                        error_message = error_data.get('detail', '')
                        
                        if 'Valid vendors:' in error_message:
                            try:
                                valid_vendors = eval(error_message.split('Valid vendors:')[1].strip())
                            except ValueError:
                                valid_vendors = []
                        
                            st.markdown("""
                                <div style='border: 2px solid #ff4444; padding: 20px; border-radius: 8px; 
                                     background-color: #fff0f0; margin: 20px auto; max-width: 800px;'>
                                    <h3 style='color: #ff4444; margin-top: 0;'>❌ Error en el Procesamiento</h3>
                                    <p style='color: #666; margin-bottom: 15px;'>
                                        Se ha detectado un ID de comercio no válido en la factura. 
                                        Por favor, asegúrate de que la factura corresponda a uno de los comercios autorizados.
                                    </p>
                            """, unsafe_allow_html=True)
                            
                            if valid_vendors:
                                st.markdown("""
                                    <div style='background-color: #fff; padding: 15px; border-radius: 5px; 
                                         border: 1px solid #ffaaaa;'>
                                        <p style='color: #666; margin-bottom: 10px;'>
                                            <strong>Comercios válidos disponibles:</strong>
                                        </p>
                                        <ul style='color: #666; margin: 0; padding-left: 20px;'>
                                """, unsafe_allow_html=True)
                                
                                for vendor in valid_vendors:
                                    st.markdown(f"""
                                        <li style='margin-bottom: 5px;'>{vendor}</li>
                                    """, unsafe_allow_html=True)
                                
                                st.markdown("""
                                        </ul>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                            else:
                                st.markdown("</div>", unsafe_allow_html=True)
                        elif "does not contain a receipt from an authorized vendor" in error_message:
                            st.markdown("""
                                <div style='border: 2px solid #ff4444; padding: 20px; border-radius: 8px; 
                                     background-color: #fff0f0; margin: 20px auto; max-width: 800px;'>
                                    <h3 style='color: #ff4444; margin-top: 0;'>❌ Error de Validación</h3>
                                    <p style='color: #666; margin-bottom: 15px;'>
                                        <strong>La imagen proporcionada no parece contener una factura de un comercio autorizado.</strong>
                                    </p>
                                    <div style='background-color: #fff; padding: 15px; border-radius: 5px; 
                                         border: 1px solid #ffaaaa;'>
                                        <p style='color: #666; margin: 0;'>
                                            ℹ️ Por favor, asegúrate de que:
                                            <ul style='margin-top: 10px;'>
                                                <li>La imagen sea clara y legible</li>
                                                <li>La factura pertenezca a uno de nuestros comercios asociados</li>
                                                <li>La imagen contenga una factura válida</li>
                                            </ul>
                                        </p>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.markdown(f"""
                                <div style='border: 2px solid #ff4444; padding: 20px; border-radius: 8px; 
                                     background-color: #fff0f0; margin: 20px auto; max-width: 800px;'>
                                    <h3 style='color: #ff4444; margin-top: 0;'>⚠️ Error en el Procesamiento</h3>
                                    <p style='color: #666; margin-bottom: 15px;'>
                                        No se pudo procesar la factura debido a un error inesperado.
                                    </p>
                                    <div style='background-color: #fff; padding: 15px; border-radius: 5px; 
                                         border: 1px solid #ffaaaa;'>
                                        <p style='color: #666; margin: 0;'>
                                            <strong>Detalles del error:</strong><br>
                                            {error_message}
                                        </p>
                                    </div>
                                </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.error(f"Error en la solicitud: {response.status_code}")
                finally:
                    # Limpiar archivos temporales después del procesamiento
                    for temp_file in temp_files:
                        try:
                            if os.path.exists(temp_file):
                                os.remove(temp_file)
                        except Exception as e:
                            st.warning(f"No se pudo eliminar el archivo temporal {temp_file}: {str(e)}")
    
    except Exception as e:
        st.error(f"Error en el procesamiento: {str(e)}")
        st.stop()

else:
    st.info("👆 Por favor, sube una imagen para procesar")
st.markdown("</div>", unsafe_allow_html=True)

# Pie de página
st.markdown("---")
st.markdown("""
    <div style='text-align: center; color: #666;'>
        <small>Desarrollado por el equipo de Moneda AI 🤖</small>
    </div>
""", unsafe_allow_html=True)