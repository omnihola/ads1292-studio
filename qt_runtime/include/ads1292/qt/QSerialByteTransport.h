#pragma once
#include "ads1292/acq/IByteTransport.h"
#include <QSerialPort>
#include <QString>
#include <vector>
#include <cstdint>

namespace ads1292 { namespace qt {

/// IByteTransport backed by a QSerialPort.
/// Opens the port at 9600 8N1 on construction; compile-only (exercised
/// against a real board — no hardware is needed for smoke tests).
class QSerialByteTransport : public ads1292::acq::IByteTransport {
 public:
  static constexpr int kDefaultTimeoutMs = 1000;

  explicit QSerialByteTransport(const QString& port_name,
                                int timeout_ms = kDefaultTimeoutMs);
  ~QSerialByteTransport() override;

  void write(const std::vector<uint8_t>& bytes) override;
  std::vector<uint8_t> read(std::size_t n) override;

 private:
  QSerialPort port_;
  int timeout_ms_;
};

}}  // namespace ads1292::qt
