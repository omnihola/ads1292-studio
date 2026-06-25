// gui/src/main.cpp
#include <QApplication>
#include <QFile>
#include <QString>
#include <QTimer>
#include "ads1292/gui/MainWindow.h"

static QString loadStyle() {
  QFile f(":/dark.qss");
  if (f.open(QFile::ReadOnly | QFile::Text)) return QString::fromUtf8(f.readAll());
  return {};
}

int main(int argc, char** argv) {
  QApplication app(argc, argv);
  app.setStyleSheet(loadStyle());

  bool smoke = false;
  for (int i = 1; i < argc; ++i) {
    if (QString::fromLocal8Bit(argv[i]) == QStringLiteral("--smoke")) smoke = true;
  }

  ads1292::gui::MainWindow window;
  window.show();

  if (smoke) {
    window.runSimulatorToCompletion(4);
    QTimer::singleShot(0, &app, &QApplication::quit);
  }
  return app.exec();
}
