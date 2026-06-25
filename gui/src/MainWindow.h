// gui/src/MainWindow.h
#pragma once
#include <QMainWindow>

namespace ads1292 {
class MainWindow : public QMainWindow {
  Q_OBJECT
public:
  explicit MainWindow(QWidget* parent = nullptr);
};
}  // namespace ads1292
