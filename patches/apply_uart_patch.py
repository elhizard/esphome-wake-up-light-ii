#!/usr/bin/env python3
"""Apply the Wake Up Light II WBR3 PA13/PA14 UART0 workaround to installed ESPHome.

This is intentionally narrow: it only adds the alternate PA13/PA14 UART0 mapping
needed by this lamp, then calls LibreTiny Serial0.setPins() before begin().
"""
from pathlib import Path
import shutil
import sys

try:
    import esphome
except ImportError:
    sys.exit("ERROR: ESPHome is not importable in this Python environment")

p = Path(esphome.__file__).parent / "components" / "uart" / "uart_component_libretiny.cpp"
if not p.exists():
    sys.exit(f"ERROR: not found: {p}")

s = p.read_text()
marker = 'Using alternate UART0 pins RX=PA13 TX=PA14'
if marker in s:
    print(f"Already patched: {p}")
    sys.exit(0)

old_select = '''#if LT_HW_UART0
  else if ((tx_pin == -1 || tx_pin == PIN_SERIAL0_TX) && (rx_pin == -1 || rx_pin == PIN_SERIAL0_RX) &&
           !should_fallback_to_software_serial()) {
    this->serial_ = &Serial0;
    this->hardware_idx_ = 0;
  }
#endif
'''
new_select = '''#if LT_HW_UART0
  else if ((((tx_pin == -1 || tx_pin == PIN_SERIAL0_TX) &&
             (rx_pin == -1 || rx_pin == PIN_SERIAL0_RX)) ||
            (tx_pin == 14 && rx_pin == 13)) &&
           !should_fallback_to_software_serial()) {
    this->serial_ = &Serial0;
    this->hardware_idx_ = 0;
  }
#endif
'''

old_begin = '  this->serial_->begin(this->baud_rate_, get_config());\n'
new_begin = '''  if (this->hardware_idx_ == 0 && tx_pin == 14 && rx_pin == 13) {
    ESP_LOGI(TAG, "Using alternate UART0 pins RX=PA13 TX=PA14");
    Serial0.setPins(rx_pin, tx_pin);
  }
  this->serial_->begin(this->baud_rate_, get_config());
'''

if old_select not in s:
    sys.exit(
        "ERROR: UART0 selection block not found. ESPHome source has changed; "
        "do not patch blindly. Compare with ESPHome issue #13596 / PR #13629."
    )
if old_begin not in s:
    sys.exit("ERROR: serial begin() line not found; ESPHome source has changed")

backup = p.with_suffix(p.suffix + ".wake-up-light-backup")
if not backup.exists():
    shutil.copy2(p, backup)
    print(f"Backup: {backup}")

s = s.replace(old_select, new_select, 1)
s = s.replace(old_begin, new_begin, 1)
p.write_text(s)
print(f"Patched: {p}")
print("Run: esphome clean wake-up-light-ii.yaml && esphome compile wake-up-light-ii.yaml")
