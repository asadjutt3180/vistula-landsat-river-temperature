"""Run the full analysis pipeline in order."""
import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
for script in ('01_match_and_qc.py', '02_calibration_validation.py', '03_loso_and_sensitivity.py',
               '04_sensor_attribution.py', '05_composites_trends_profile.py'):
    print('\n' + '=' * 70 + '\n' + script + '\n' + '=' * 70)
    runpy.run_path(str(HERE / script), run_name='__main__')
