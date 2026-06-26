// qt_runtime/src/QSerialByteTransport.cpp
#include "ads1292/qt/QSerialByteTransport.h"
#include <QByteArray>
#include <stdexcept>

namespace ads1292 { namespace qt {

QSerialByteTransport::QSerialByteTransport(const QString& port_name,
                                           int timeout_ms)
    : timeout_ms_(timeout_ms) {
  port_.setPortName(port_name);
  port_.setBaudRate(QSerialPort::Baud9600);
  port_.setDataBits(QSerialPort::Data8);
  port_.setParity(QSerialPort::NoParity);
  port_.setStopBits(QSerialPort::OneStop);
  port_.setFlowControl(QSerialPort::NoFlowControl);

  if (!port_.open(QIODevice::ReadWrite)) {
    throw std::runtime_error(
        "QSerialByteTransport: failed to open port " +
        port_name.toStdString() + ": " +
        port_.errorString().toStdString());
  }
}

QSerialByteTransport::~QSerialByteTransport() {
  if (port_.isOpen()) {
    port_.close();
  }
}

void QSerialByteTransport::write(const std::vector<uint8_t>& bytes) {
  const QByteArray data(reinterpret_cast<const char*>(bytes.data()),
                        static_cast<qsizetype>(bytes.size()));
  // B4: check write count and flush success; throw on failure (oracle: pyserial raises on write error)
  if (port_.write(data) != static_cast<qint64>(data.size()) ||
      !port_.waitForBytesWritten(timeout_ms_)) {
    throw std::runtime_error("serial write failed");
  }
}

std::vector<uint8_t> QSerialByteTransport::read(std::size_t n) {
  std::vector<uint8_t> result;
  result.reserve(n);

  while (result.size() < n) {
    if (!port_.waitForReadyRead(timeout_ms_)) {
      break;  // timeout — return what we have (may be fewer than n)
    }
    const QByteArray chunk = port_.read(
        static_cast<qint64>(n - result.size()));
    for (char c : chunk) {
      result.push_back(static_cast<uint8_t>(c));
    }
  }
  return result;
}

}}  // namespace ads1292::qt
