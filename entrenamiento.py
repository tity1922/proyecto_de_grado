import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import models, transforms, datasets
from torch.utils.data import DataLoader, WeightedRandomSampler, random_split, ConcatDataset
import os
import time

# ==========================================
# 0. DIAGNÓSTICO DE HARDWARE
# ==========================================
print("="*50)
print("🔍 COMPROBANDO SISTEMA DE ENTRENAMIENTO...")
if torch.cuda.is_available():
    device = torch.device("cuda")
    print(f"✅ ESTADO: Usando GPU (NVIDIA CUDA)")
    print(f"🎮 DISPOSITIVO: {torch.cuda.get_device_name(0)}")
    print(f"💾 MEMORIA TOTAL: {torch.cuda.get_device_properties(0).total_memory / 1024**2:.0f} MB")
else:
    device = torch.device("cpu")
    print("⚠️ ESTADO: GPU no detectada. Usando CPU (Será más lento).")
print("="*50)

# ==========================================
# 1. CONFIGURACIÓN DE RUTAS
# ==========================================
data_dir_original = r'D:\carva\Escritorio\esp32cam\Proyecto_Grado\Garbage classification'
data_dir_refuerzo = r'D:\carva\Escritorio\esp32cam\Proyecto_Grado\Dataset_Refuerzo'
MODEL_SAVE_PATH = 'garbage_model_binario_UDI.pth'

# Mapeos
mapping_original = {
    'cardboard': 0, 'glass': 0, 'metal': 0, 'paper': 0, 'plastic': 0, 
    'trash': 1 
}
mapping_refuerzo = {
    '1_aprovechable': 0,
    '2_no_aprovechable': 1
}

# ==========================================
# 2. CARGA DE DATOS
# ==========================================
class BinaryDataset(datasets.ImageFolder):
    def __init__(self, root, transform=None, custom_mapping=None):
        super().__init__(root, transform=transform)
        self.custom_mapping = custom_mapping

    def __getitem__(self, index):
        path, _ = self.samples[index]
        label_name = os.path.basename(os.path.dirname(path))
        target = self.custom_mapping[label_name]
        img = self.loader(path).convert('RGB')
        if self.transform: img = self.transform(img)
        return img, target

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomRotation(20),
    transforms.ColorJitter(brightness=0.3, contrast=0.3),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

ds_original = BinaryDataset(data_dir_original, transform=transform, custom_mapping=mapping_original)
ds_refuerzo = BinaryDataset(data_dir_refuerzo, transform=transform, custom_mapping=mapping_refuerzo)
dataset_final = ConcatDataset([ds_original, ds_refuerzo])

print(f"📊 Total imágenes: {len(dataset_final)} (Original: {len(ds_original)} + Refuerzo: {len(ds_refuerzo)})")

# Split
train_size = int(0.8 * len(dataset_final))
val_size = len(dataset_final) - train_size
train_dataset, val_dataset = random_split(dataset_final, [train_size, val_size])

# Sampler para balanceo
def get_targets(subset):
    targets = []
    for idx in subset.indices:
        if idx < len(ds_original):
            path, _ = ds_original.samples[idx]
            targets.append(mapping_original[os.path.basename(os.path.dirname(path))])
        else:
            path, _ = ds_refuerzo.samples[idx - len(ds_original)]
            targets.append(mapping_refuerzo[os.path.basename(os.path.dirname(path))])
    return targets

targets_train = get_targets(train_dataset)
class_counts = torch.bincount(torch.tensor(targets_train))
weights = 1. / class_counts.float()
samples_weights = weights[targets_train]
sampler = WeightedRandomSampler(samples_weights, len(samples_weights), replacement=True)

# DataLoaders ajustados a la GTX 1650 (batch_size=16)
train_loader = DataLoader(train_dataset, batch_size=16, sampler=sampler, pin_memory=True)
val_loader = DataLoader(val_dataset, batch_size=16, shuffle=False, pin_memory=True)

# ==========================================
# 3. MODELO Y PENALIZACIÓN
# ==========================================
model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
num_ftrs = model.fc.in_features
model.fc = nn.Sequential(
    nn.Linear(num_ftrs, 512),
    nn.ReLU(),
    nn.Dropout(0.5),
    nn.Linear(512, 2) 
)
model = model.to(device)

# Penalización 10x para Clase 1 (Trash/No Aprovechable)
pesos_penalidad = torch.tensor([1.0, 10.0]).to(device)
criterion = nn.CrossEntropyLoss(weight=pesos_penalidad)
optimizer = optim.Adam(model.parameters(), lr=0.00001)

# ==========================================
# 4. BUCLE DE ENTRENAMIENTO
# ==========================================
num_epochs = 10
print("\n🚀 INICIANDO ENTRENAMIENTO...")
start_time = time.time()

for epoch in range(num_epochs):
    model.train()
    running_loss = 0.0
    
    for inputs, labels in train_loader:
        inputs, labels = inputs.to(device, non_blocking=True), labels.to(device, non_blocking=True)
        
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        running_loss += loss.item()

    # Validación al final de cada época
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, labels in val_loader:
            inputs, labels = inputs.to(device), labels.to(device)
            outputs = model(inputs)
            _, predicted = torch.max(outputs, 1)
            total += labels.size(0)
            correct += (predicted == labels).sum().item()
    
    # Liberar caché para evitar saturar la GTX 1650
    torch.cuda.empty_cache()
    
    acc = 100 * correct / total
    print(f"Epoch [{epoch+1}/{num_epochs}] - Loss: {running_loss/len(train_loader):.4f} - Val Acc: {acc:.2f}%")

end_time = time.time()
print(f"\n✅ Entrenamiento terminado en: {(end_time - start_time)/60:.2f} minutos")

# Guardar modelo
torch.save(model.state_dict(), MODEL_SAVE_PATH)
print(f"💾 Modelo ultra-robusto guardado como: {MODEL_SAVE_PATH}")