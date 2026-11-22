// SPDX-FileCopyrightText: 2026 Rehab Agent meta-repo contributors
// SPDX-License-Identifier: CERN-OHL-S-2.0
//
// Bench readout for the sensor sole and its coupon (BUILD.md, part 3): Seeed XIAO nRF52840 (Sense or not),
// a CD74HC4067 16:1 multiplexer and a dual rail-to-rail op-amp as two transimpedance amplifiers.
//
// Circuit (BUILD.md has the full wiring):
//   - the common comb is at GND;
//   - each sense line is held at Vbias (about 0.5 V) by the selected amplifier's inverting input, so the film's
//     conductance G draws I = Vbias * G and the output is Vout = Vbias * (1 + Rf * G);
//   - A0: the multiplexed amplifier's output; A1: the reference cell's own amplifier; A2: Vbias itself.
//   Reading Vbias on A2 makes the conversion ratiometric: G = (Vout / Vbias - 1) / Rf, whatever the ADC
//   reference is. The host does that conversion (log_bench.py); this sketch sends raw counts.
//
// Serial protocol, 115200 baud, one line each:
//   H,<key=value>,...                 header, at start and after every setting change
//   F,<t_us>,<sync_n>,<sync_t_us>,<vbias>,<ref>,<c0>,...,<cN-1>   one frame
//   commands (send a line): L<n> lines 1-16 | S<us> settle time | O<n> oversampling 1-16 | P<ms> frame period |
//                           R<ohm> multiplexed Rf | Q<ohm> reference Rf (both only recorded in the header)
//
// Status: written for the bench, compiled only against a stub of the Arduino API (BUILD.md). Not yet built,
// flashed or run on the hardware.

const char *FW = "sole_bench 0.1";

const uint8_t MUX_S[4] = {7, 8, 9, 10};   // D7..D10 -> S0..S3 (EN tied to GND)
const uint8_t PIN_OUT = A0;               // multiplexed amplifier
const uint8_t PIN_REF = A1;               // reference cell's amplifier
const uint8_t PIN_VBIAS = A2;             // the bias voltage, for the ratiometric conversion
const uint8_t PIN_SYNC = 6;               // D6: sync pulse in (rising edge), pull-down

uint8_t lines = 4;                        // the coupon's 4 cells (C0-C3); the sole: L16
uint16_t settle_us = 300;                 // after switching the multiplexer
uint8_t oversample = 4;
uint16_t period_ms = 10;                  // 100 Hz frames
uint32_t rf_ohm = 100000, rf_ref_ohm = 100000;

volatile uint32_t sync_n = 0, sync_t = 0;
void on_sync() { sync_n++; sync_t = micros(); }

void select_line(uint8_t ch) {
  for (uint8_t b = 0; b < 4; b++) digitalWrite(MUX_S[b], (ch >> b) & 1);
}

uint32_t read_avg(uint8_t pin) {
  uint32_t s = 0;
  for (uint8_t k = 0; k < oversample; k++) s += analogRead(pin);
  return s / oversample;
}

void header() {
  Serial.print("H,fw="); Serial.print(FW);
  Serial.print(",lines="); Serial.print(lines);
  Serial.print(",settle_us="); Serial.print(settle_us);
  Serial.print(",oversample="); Serial.print(oversample);
  Serial.print(",period_ms="); Serial.print(period_ms);
  Serial.print(",rf_ohm="); Serial.print(rf_ohm);
  Serial.print(",rf_ref_ohm="); Serial.print(rf_ref_ohm);
  Serial.println(",adc_bits=12");
}

void command(const char *s) {
  long v = atol(s + 1);
  switch (s[0]) {
    case 'L': if (v >= 1 && v <= 16) lines = v; break;
    case 'S': if (v >= 10 && v <= 20000) settle_us = v; break;
    case 'O': if (v >= 1 && v <= 16) oversample = v; break;
    case 'P': if (v >= 5 && v <= 1000) period_ms = v; break;
    case 'R': if (v > 0) rf_ohm = v; break;
    case 'Q': if (v > 0) rf_ref_ohm = v; break;
    default: return;
  }
  header();
}

void setup() {
  Serial.begin(115200);
  for (uint8_t b = 0; b < 4; b++) pinMode(MUX_S[b], OUTPUT);
  pinMode(PIN_SYNC, INPUT_PULLDOWN);
  attachInterrupt(digitalPinToInterrupt(PIN_SYNC), on_sync, RISING);
  analogReadResolution(12);
  select_line(0);
  delay(500);
  header();
}

char buf[24];
uint8_t nbuf = 0;
uint32_t next_ms = 0;

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') { if (nbuf) { buf[nbuf] = 0; command(buf); nbuf = 0; } }
    else if (nbuf < sizeof(buf) - 1) buf[nbuf++] = c;
  }
  if ((int32_t)(millis() - next_ms) < 0) return;
  next_ms = millis() + period_ms;

  uint32_t t = micros();
  uint32_t vb = read_avg(PIN_VBIAS), ref = read_avg(PIN_REF);
  uint32_t c[16];
  for (uint8_t ch = 0; ch < lines; ch++) {
    select_line(ch);
    delayMicroseconds(settle_us);
    c[ch] = read_avg(PIN_OUT);
  }
  noInterrupts(); uint32_t sn = sync_n, st = sync_t; interrupts();
  Serial.print("F,"); Serial.print(t); Serial.print(','); Serial.print(sn); Serial.print(','); Serial.print(st);
  Serial.print(','); Serial.print(vb); Serial.print(','); Serial.print(ref);
  for (uint8_t ch = 0; ch < lines; ch++) { Serial.print(','); Serial.print(c[ch]); }
  Serial.println();
}
