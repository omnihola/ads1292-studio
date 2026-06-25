// gui/src/MainWindow.cpp
#include "MainWindow.h"
#include <QLabel>

namespace ads1292 {
MainWindow::MainWindow(QWidget* parent) : QMainWindow(parent) {
  setWindowTitle("ADS1292 Studio");
  resize(1100, 700);
  auto* title = new QLabel("ADS1292 Studio", this);
  title->setObjectName("TitleLabel");
  title->setAlignment(Qt::AlignCenter);
  setCentralWidget(title);
}
}  // namespace ads1292
