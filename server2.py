import torch
import torch.nn as nn
from torchvision import models, transforms
from flask import Flask, request
from PIL import Image
import io
import os

app = Flask(__name__)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

# --- 1. CONFIGURACIÓN DEL MODELO ---
def cargar_modelo():
    # Arquitectura idéntica al entrenamiento v10.0 (512 neuronas)
    model = models.resnet50()
    num_ftrs = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Linear(num_ftrs, 512), 
        nn.ReLU(),
        nn.Dropout(0.4),
        nn.Linear(512, 2)
    )
    
    # Asegúrate de que el archivo generado por el entrenamiento v10.0 esté en esta carpeta
    path = 'garbage_model_binario_UDI.pth'
    
    if os.path.exists(path):
        try:
            model.load_state_dict(torch.load(path, map_location=device))
            model.to(device)
            model.eval()
            print(f"✅ Servidor: Modelo equilibrado cargado exitosamente.")
            return model
        except Exception as e:
            print(f"❌ Error de dimensiones (Mismatch): {e}")
            print("Asegúrate de haber entrenado con el código de 512 neuronas.")
            return None
    else:
        print(f"❌ No se encontró el archivo: {path}")
        return None

global_model = cargar_modelo()

# Transformaciones estándar para ResNet-50
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

@app.route('/clasificar', methods=['POST'])
def clasificar():
    if global_model is None:
        return "Error: Modelo no cargado", 500

    try:
        # Recibir imagen de la ESP32-CAM
        img_bytes = request.data
        if not img_bytes:
            return "Sin datos", 400

        imagen = Image.open(io.BytesIO(img_bytes)).convert('RGB')
        
        # Pre-procesamiento
        img_t = transform(imagen).unsqueeze(0).to(device)
        
        with torch.no_grad():
            output = global_model(img_t)
            # Calculamos probabilidades (0.0 a 1.0)
            probabilidades = torch.nn.functional.softmax(output, dim=1)
            confianza, prediccion = torch.max(probabilidades, 1)
        
        indice = prediccion.item()
        conf = confianza.item()

        # --- LÓGICA DE EQUILIBRIO (UMBRAL DEL 75%) ---
        # Si la IA dice 'Aprovechable' (0) pero tiene dudas (conf < 0.75), 
        # lo mandamos a 'No Aprovechable' (2) por seguridad.
        if indice == 0 and conf < 0.75:
            token = "2"
            resultado_texto = "DUDA (RECLASIFICADO A NO APROVECHABLE)"
        else:
            # 0 -> Token 1 (Aprovechable) | 1 -> Token 2 (No Aprovechable)
            token = "1" if indice == 0 else "2"
            resultado_texto = "APROVECHABLE" if token == "1" else "NO APROVECHABLE"

        # Logs para monitorear en tiempo real desde Bucaramanga
        print(f"\n--- Clasificación Recibida ---")
        print(f"Confianza: {conf * 100:.2f}%")
        print(f"Resultado Final: {resultado_texto} (Token {token})")

        return token, 200

    except Exception as e:
        print(f"❌ Error procesando imagen: {e}")
        return "error", 500

if __name__ == '__main__':
    # host='0.0.0.0' permite que la ESP32-CAM se conecte a tu PC
    print("🚀 Servidor de Grado UDI corriendo en puerto 5000...")
    app.run(host='0.0.0.0', port=5000)