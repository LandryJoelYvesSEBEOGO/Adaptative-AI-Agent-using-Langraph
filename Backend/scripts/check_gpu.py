import torch

print("=" * 50)
print("VÉRIFICATION GPU/CUDA")
print("=" * 50)

# Vérifier si PyTorch est installé
print(f"PyTorch version: {torch.__version__}")

# Vérifier si CUDA est disponible
print(f"CUDA disponible: {torch.cuda.is_available()}")

if torch.cuda.is_available():
    print(f"Nombre de GPUs: {torch.cuda.device_count()}")
    print(f"Nom du GPU: {torch.cuda.get_device_name(0)}")
    print(f"Version CUDA: {torch.version.cuda}")
    print(f"Capacité de calcul: {torch.cuda.get_device_capability(0)}")
    
    # Test d'allocation mémoire
    try:
        x = torch.randn(3, 3).cuda()
        print("✅ Test GPU réussi: allocation mémoire OK")
    except Exception as e:
        print(f"❌ Erreur lors du test GPU: {e}")
else:
    print("❌ CUDA n'est pas disponible")
    print("   Raisons possibles:")
    print("   - Pas de GPU NVIDIA installé")
    print("   - Pilotes NVIDIA non installés")
    print("   - PyTorch installé sans support CUDA")
    print("   - PyTorch CPU-only installé")
print("=" * 50)