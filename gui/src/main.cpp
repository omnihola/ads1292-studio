// gui/src/main.cpp
#include <QApplication>
#include <QFile>
#include <QString>
#include <QTimer>
#include "MainWindow.h"

static QString loadStyle() {
  QFile f(":/dark.qss");
  if (f.open(QFile::ReadOnly | QFile::Text)) {
    return QString::fromUtf8(f.readAll());
  }
  return QString();
}

int main(int argc, char** argv) {
  QApplication app(argc, argv);
  app.setStyleSheet(loadStyle());

  ads1292::MainWindow window;
  window.show();

  bool smoke = false;
  for (int i = 1; i < argc; ++i) {
    if (QString::fromLocal8Bit(argv[i]) == QStringLiteral("--smoke")) {
      smoke = true;
    }
  }
  if (smoke) {
    QTimer::singleShot(0, &app, &QApplication::quit);
  }
  return app.exec();
}
