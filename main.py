"""Inicializa o Astra Sender, com coordenadas DPI-aware em monitores Windows."""
import sys


def enable_dpi_awareness():
    if sys.platform != 'win32':
        return
    try:
        import ctypes
        # Coordenadas fisicas para mouse e seletores, inclusive em alta escala de DPI.
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (OSError, AttributeError):
        try:
            import ctypes
            ctypes.windll.user32.SetProcessDPIAware()
        except (OSError, AttributeError):
            pass


def main():
    enable_dpi_awareness()
    from PySide6.QtWidgets import QApplication, QMessageBox
    from app.database.db import initialize_database
    from app.ui.main_window import MainWindow
    app = QApplication(sys.argv)
    app.setApplicationName('Astra Sender')
    app.setOrganizationName('Astra Sender')
    try:
        initialize_database()
    except Exception as e:
        QMessageBox.critical(None, 'Erro no banco de dados',
                             f'Astra Sender não conseguiu abrir seus dados.\n\n{e}')
        return 1
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == '__main__':
    sys.exit(main())
