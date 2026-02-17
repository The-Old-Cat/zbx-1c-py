import subprocess
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent / "src"))

from zbx_1c.core.config import Settings


def test_direct():
    """Прямой тест без использования менеджера"""
    settings = Settings()

    # Прямая команда как в рабочем примере
    cmd = [str(settings.rac_path), "cluster", "list", f"{settings.rac_host}:{settings.rac_port}"]

    print(f"Executing: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30)

        print(f"Return code: {result.returncode}")

        # Пробуем разные кодировки
        for enc in ["cp866", "cp1251", "utf-8"]:
            try:
                stdout = result.stdout.decode(enc)
                print(f"\nEncoding {enc}:")
                print(stdout[:500])
                if "cluster" in stdout.lower():
                    print(f"✅ Found clusters with {enc}")
                    break
            except:
                continue

    except Exception as e:
        print(f"Error: {e}")


def test_through_manager():
    """Тест через менеджер"""
    from zbx_1c.monitoring.cluster.manager import ClusterManager

    settings = Settings()
    manager = ClusterManager(settings)

    print("\nTesting through ClusterManager:")
    clusters = manager.discover_clusters()
    print(f"Found {len(clusters)} clusters")
    for c in clusters:
        print(f"  - {c.name} ({c.id})")


if __name__ == "__main__":
    test_direct()
    test_through_manager()
