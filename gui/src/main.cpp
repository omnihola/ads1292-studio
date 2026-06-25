// gui/src/main.cpp
#include <QApplication>
#include <QFile>
#include <QString>
#include <QTimer>
#include "ads1292/gui/MainWindow.h"
#include "ads1292/gui/ReportExport.h"
#include "ads1292/io/CsvIo.h"
#include <cstdio>
#include <string>

static QString loadStyle() {
  QFile f(":/dark.qss");
  if (f.open(QFile::ReadOnly | QFile::Text)) return QString::fromUtf8(f.readAll());
  return {};
}

int main(int argc, char** argv) {
  QApplication app(argc, argv);
  app.setStyleSheet(loadStyle());

  bool smoke = false;
  std::string export_csv, export_outdir;
  for (int i = 1; i < argc; ++i) {
    QString arg = QString::fromLocal8Bit(argv[i]);
    if (arg == QStringLiteral("--smoke")) {
      smoke = true;
    } else if (arg == QStringLiteral("--export-report") && i + 2 < argc) {
      export_csv    = argv[i + 1];
      export_outdir = argv[i + 2];
      i += 2;
    }
  }

  // --export-report <csv> <outdir>: headless report generation, then exit.
  if (!export_csv.empty()) {
    auto samples = ads1292::io::read_recording_csv(export_csv);
    auto r = ads1292::gui::export_review_report(samples, export_outdir);
    std::printf("html:     %s\n", r.html_path.c_str());
    std::printf("ecg_png:  %s\n", r.ecg_png_path.c_str());
    std::printf("pqrst_png:%s\n", r.pqrst_png_path.c_str());
    std::printf("spec_png: %s\n", r.spectrum_png_path.c_str());
    return 0;
  }

  ads1292::gui::MainWindow window;
  window.show();

  if (smoke) {
    window.runSimulatorToCompletion(4);
    QTimer::singleShot(0, &app, &QApplication::quit);
  }
  return app.exec();
}
