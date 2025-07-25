import sys
import os
import traceback
import tempfile
from PyQt6.QtWidgets import (QApplication, QMainWindow, QSplitter, QMenuBar, QMenu, 
                           QFileDialog, QTextEdit, QDockWidget, QListWidget, QMessageBox, 
                           QTabWidget, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, 
                           QLabel, QComboBox, QToolBar, QStatusBar)
from PyQt6.QtGui import QFont, QColor, QAction, QSyntaxHighlighter, QTextCharFormat
from PyQt6.QtCore import Qt, QRegularExpression

# Import assembler components
from assembler.parser import Parser
from assembler.asm import Program
from assembler.asm.formatters import HexFormatter, AsmFormatter
from assembler.expression import ExpressionException
from assembler.parser import ParserException
from assembler.asm import InstructionException

class AssemblerHighlighter(QSyntaxHighlighter):
    """Custom syntax highlighter for the assembler language."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create highlighting rules
        self.highlighting_rules = []
        
        # Instructions
        instruction_format = QTextCharFormat()
        instruction_format.setForeground(QColor("#0000FF"))  # Blue
        instruction_format.setFontWeight(QFont.Weight.Bold)
        
        # Get all instructions from the PDF
        instruction_patterns = [
            "NOP", "MOV", "ADD", "ADC", "SUB", "SBC", "AND", "OR", "EOR", 
            "LDI", "LDIs", "ADDI", "ADDIs", "ADCI", "ADCIs", "SUBI", "SUBIs", 
            "SBCI", "SBCIs", "NEG", "ANDI", "ANDIs", "ORI", "ORIs", "EORI", 
            "EORIs", "NOT", "MUL", "MULs", "MULSs", "CP", "CPI", "CPIs",
            "JMP", "JMPI", "BRCS", "BRCC", "BRMI", "BRPL", "BREQ", "BRNE", 
            "BRVS", "BRVC", "BRLT", "BRGE", "BRLE", "BRGT", "BRK", "RETI",
            "ST", "LD", "STS", "STSs", "LDS", "LDSs", "STD", "LDD", "LDDd",
            "OUT", "OUTs", "OUTR", "IN", "INs", "INR"
        ]
        
        for pattern in instruction_patterns:
            regex = QRegularExpression(r"\b" + pattern + r"\b")
            self.highlighting_rules.append((regex, instruction_format))
        
        # Macros
        macro_format = QTextCharFormat()
        macro_format.setForeground(QColor("#0099CC"))  # Light blue
        macro_format.setFontWeight(QFont.Weight.Bold)
        
        macro_patterns = [
            "POP", "RET", "CALL", "DEC", "LEAVE", "LEAVEI", "ENTER", 
            "ENTERI", "_SCALL", "PUSH", "INC"
        ]
        
        for pattern in macro_patterns:
            regex = QRegularExpression(r"\b" + pattern + r"\b")
            self.highlighting_rules.append((regex, macro_format))
        
        # Directives
        directive_format = QTextCharFormat()
        directive_format.setForeground(QColor("#FF6600"))  # Orange
        directive_format.setFontWeight(QFont.Weight.Bold)
        
        directive_patterns = [
            r"\.reg", r"\.long", r"\.org", r"\.const", r"\.include", r"\.word", r"\.dorg", r"\.data"
        ]
        
        for pattern in directive_patterns:
            regex = QRegularExpression(pattern)
            self.highlighting_rules.append((regex, directive_format))
        
        # Registers
        register_format = QTextCharFormat()
        register_format.setForeground(QColor("#AA00AA"))  # Purple
        
        # Standard registers (R0-R31) and special registers
        for i in range(32):
            regex = QRegularExpression(r"\bR" + str(i) + r"\b")
            self.highlighting_rules.append((regex, register_format))
        
        # Special registers
        special_registers = ["SP", "PC", "BP", "RA"]
        for reg in special_registers:
            regex = QRegularExpression(r"\b" + reg + r"\b")
            self.highlighting_rules.append((regex, register_format))
        
        # Numbers
        number_format = QTextCharFormat()
        number_format.setForeground(QColor("#009900"))  # Green
        
        # Decimal numbers
        self.highlighting_rules.append((QRegularExpression(r"\b\d+\b"), number_format))
        # Hex numbers
        self.highlighting_rules.append((QRegularExpression(r"\b0x[0-9A-Fa-f]+\b"), number_format))
        # Binary numbers
        self.highlighting_rules.append((QRegularExpression(r"\b0b[01]+\b"), number_format))
        
        # Comments
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#808080"))  # Gray
        self.highlighting_rules.append((QRegularExpression(r";.*"), comment_format))
        
        # Labels
        label_format = QTextCharFormat()
        label_format.setForeground(QColor("#990099"))  # Magenta
        self.highlighting_rules.append((QRegularExpression(r"^\s*\w+:"), label_format))
        
        # Strings
        string_format = QTextCharFormat()
        string_format.setForeground(QColor("#990000"))  # Red
        self.highlighting_rules.append((QRegularExpression(r"\".*\""), string_format))
    
    def highlightBlock(self, text):
        """Apply syntax highlighting to the given block of text."""
        for pattern, format in self.highlighting_rules:
            match_iterator = pattern.globalMatch(text)
            while match_iterator.hasNext():
                match = match_iterator.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)


class AssemblerEditor(QTextEdit):
    """Custom text editor for assembly code with line numbers."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Set up the editor
        self.setup_editor()
        
        # Current file being edited
        self.current_file = None
        self.modified = False
        
        # Set up the highlighter
        self.highlighter = AssemblerHighlighter(self.document())
        
        # Connect signals
        self.textChanged.connect(self.on_text_changed)
    
    def setup_editor(self):
        """Configure the editor settings."""
        # Set a fixed-width font
        font = QFont("Consolas", 11)
        self.setFont(font)
        
        # Set tab stops
        metrics = self.fontMetrics()
        self.setTabStopDistance(4 * metrics.horizontalAdvance(' '))
    
    def on_text_changed(self):
        """Handle text changes in the editor."""
        self.modified = True
    
    def new_file(self):
        """Create a new file."""
        self.clear()
        self.current_file = None
        self.modified = False
        
    def open_file(self, filename=None):
        """Open a file in the editor."""
        if not filename:
            filename, _ = QFileDialog.getOpenFileName(
                self, "Open File", "", "Assembly Files (*.asm);;All Files (*)"
            )
        
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    text = f.read()
                self.setText(text)
                self.current_file = filename
                self.modified = False
                return True
            except Exception as e:
                QMessageBox.critical(self, "Error Opening File", str(e))
        
        return False
    
    def save_file(self, filename=None):
        """Save the current file."""
        if not filename and not self.current_file:
            return self.save_file_as()
        
        filename = filename or self.current_file
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(self.toPlainText())
            self.current_file = filename
            self.modified = False
            return True
        except Exception as e:
            QMessageBox.critical(self, "Error Saving File", str(e))
            return False
    
    def save_file_as(self):
        """Save the current file with a new name."""
        filename, _ = QFileDialog.getSaveFileName(
            self, "Save File As", "", "Assembly Files (*.asm);;All Files (*)"
        )
        
        if filename:
            return self.save_file(filename)
        
        return False


class LineNumberArea(QWidget):
    """Widget for displaying line numbers."""
    
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
    
    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)
    
    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)


class OutputConsole(QTextEdit):
    """Console widget for displaying assembler output and errors."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont("Consolas", 10))
        self.setStyleSheet("background-color: #F0F0F0;")
    
    def append_message(self, text, color="black"):
        """Append a colored message to the console."""
        self.setTextColor(QColor(color))
        self.append(text)
    
    def clear_console(self):
        """Clear the console."""
        self.clear()


class InstructionReferenceWidget(QWidget):
    """Widget for displaying instruction set reference."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.layout = QVBoxLayout(self)
        
        # Create search/filter controls
        search_layout = QHBoxLayout()
        self.search_input = QComboBox()
        self.search_input.setEditable(True)
        
        # Add all instructions from the PDF
        self.search_input.addItems([
            "NOP", "MOV", "ADD", "ADC", "SUB", "SBC", "AND", "OR", "EOR", 
            "LDI", "LDIs", "ADDI", "ADDIs", "ADCI", "ADCIs", "SUBI", "SUBIs", 
            "SBCI", "SBCIs", "NEG", "ANDI", "ANDIs", "ORI", "ORIs", "EORI", 
            "EORIs", "NOT", "MUL", "MULs", "MULSs", "CP", "CPI", "CPIs",
            "JMP", "JMPI", "BRCS", "BRCC", "BRMI", "BRPL", "BREQ", "BRNE", 
            "BRVS", "BRVC", "BRLT", "BRGE", "BRLE", "BRGT", "BRK", "RETI",
            "ST", "LD", "STS", "STSs", "LDS", "LDSs", "STD", "LDD", "LDDd",
            "OUT", "OUTs", "OUTR", "IN", "INs", "INR",
            "POP", "RET", "CALL", "DEC", "LEAVE", "LEAVEI", "ENTER", 
            "ENTERI", "_SCALL", "PUSH", "INC"
        ])
        
        self.search_input.currentTextChanged.connect(self.update_instruction_details)
        search_layout.addWidget(QLabel("Instruction:"))
        search_layout.addWidget(self.search_input)
        
        self.layout.addLayout(search_layout)
        
        # Create details display
        self.details = QTextEdit()
        self.details.setReadOnly(True)
        self.details.setFont(QFont("Consolas", 10))
        self.layout.addWidget(self.details)
        
        # Initialize with first instruction
        self.update_instruction_details(self.search_input.currentText())
    
    def update_instruction_details(self, instruction):
        """Update the details for the selected instruction."""
        # Complete instruction set from the PDF
        instruction_details = {
            # Regular instructions
            "NOP": {"opcode": "0x0", "desc": "Does nothing."},
            "MOV": {"opcode": "0x1", "desc": "Move the content of Rs to register Rd.", "format": "MOV Rd,Rs"},
            "ADD": {"opcode": "0x2", "desc": "Adds the content of register Rs to register Rd without carry.", "format": "ADD Rd,Rs"},
            "ADC": {"opcode": "0x3", "desc": "Adds the content of register Rs to register Rd with carry.", "format": "ADC Rd,Rs"},
            "SUB": {"opcode": "0x4", "desc": "Subtracts the content of register Rs from register Rd without carry.", "format": "SUB Rd,Rs"},
            "SBC": {"opcode": "0x5", "desc": "Subtracts the content of register Rs from register Rd with carry.", "format": "SBC Rd,Rs"},
            "AND": {"opcode": "0x6", "desc": "Stores Rs and Rd in register Rd.", "format": "AND Rd,Rs"},
            "OR": {"opcode": "0x7", "desc": "Stores Rs or Rd in register Rd.", "format": "OR Rd,Rs"},
            "EOR": {"opcode": "0x8", "desc": "Stores Rs xor Rd in register Rd.", "format": "EOR Rd,Rs"},
            "LDI": {"opcode": "0x9", "desc": "Loads Register Rd with the constant value [const].", "format": "LDI Rd,[const]"},
            "LDIs": {"opcode": "0xa", "desc": "Loads Register Rd with the constant value [const]. (0<=[const]<=15)", "format": "LDIs Rd,[const]"},
            "ADDI": {"opcode": "0xb", "desc": "Adds the constant [const] to register Rd without carry.", "format": "ADDI Rd,[const]"},
            "ADDIs": {"opcode": "0xc", "desc": "Adds the constant [const] to register Rd without carry. (0<=[const]<=15)", "format": "ADDIs Rd,[const]"},
            "ADCI": {"opcode": "0xd", "desc": "Adds the constant [const] to register Rd with carry.", "format": "ADCI Rd,[const]"},
            "ADCIs": {"opcode": "0xe", "desc": "Adds the constant [const] to register Rd with carry. (0<=[const]<=15)", "format": "ADCIs Rd,[const]"},
            "SUBI": {"opcode": "0xf", "desc": "Subtracts a constant [const] from register Rd without carry.", "format": "SUBI Rd,[const]"},
            "SUBIs": {"opcode": "0x10", "desc": "Subtracts a constant [const] from register Rd without carry. (0<=[const]<=15)", "format": "SUBIs Rd,[const]"},
            "SBCI": {"opcode": "0x11", "desc": "Subtracts a constant [const] from register Rd with carry.", "format": "SBCI Rd,[const]"},
            "SBCIs": {"opcode": "0x12", "desc": "Subtracts a constant [const] from register Rd with carry. (0<=[const]<=15)", "format": "SBCIs Rd,[const]"},
            "NEG": {"opcode": "0x13", "desc": "Stores the two's complement of Rd in register Rd.", "format": "NEG Rd"},
            "ANDI": {"opcode": "0x14", "desc": "Stores Rd and [const] in register Rd.", "format": "ANDI Rd,[const]"},
            "ANDIs": {"opcode": "0x15", "desc": "Stores Rd and [const] in register Rd. (0<=[const]<=15)", "format": "ANDIs Rd,[const]"},
            "ORI": {"opcode": "0x16", "desc": "Stores Rd or [const] in register Rd.", "format": "ORI Rd,[const]"},
            "ORIs": {"opcode": "0x17", "desc": "Stores Rd or [const] in register Rd. (0<=[const]<=15)", "format": "ORIs Rd,[const]"},
            "EORI": {"opcode": "0x18", "desc": "Stores Rd xor [const] in register Rd.", "format": "EORI Rd,[const]"},
            "EORIs": {"opcode": "0x19", "desc": "Stores Rd xor [const] in register Rd. (0<=[const]<=15)", "format": "EORIs Rd,[const]"},
            "NOT": {"opcode": "0x1a", "desc": "Stores the one's complement of Rd in register Rd.", "format": "NOT Rd"},
            "MUL": {"opcode": "0x1b", "desc": "Multiplies Rd and Rs and stores the result in Rd.", "format": "MUL Rd,Rs"},
            "MULs": {"opcode": "0x1c", "desc": "Multiplies Rd and the constant [const] and stores the result in Rd.", "format": "MULs Rd,[const]"},
            "MULSs": {"opcode": "0x1d", "desc": "Multiplies Rd and the constant [const] and stores the result in Rd. (0<=[const]<=15)", "format": "MULSs Rd,[const]"},
            "CP": {"opcode": "0x1e", "desc": "Compares registers Rd and Rs.", "format": "CP Rd,Rs"},
            "CPI": {"opcode": "0x1f", "desc": "Compares register Rd with the constant [const].", "format": "CPI Rd,[const]"},
            "CPIs": {"opcode": "0x20", "desc": "Compares register Rd with the constant [const]. (0<=[const]<=15)", "format": "CPIs Rd,[const]"},
            "JMP": {"opcode": "0x21", "desc": "Jumps to address given by register Rs.", "format": "JMP Rs"},
            "JMPI": {"opcode": "0x22", "desc": "Jumps to address given by the constant [const].", "format": "JMPI [const]"},
            "BRCS": {"opcode": "0x23", "desc": "Branch if carry set.", "format": "BRCS [const]"},
            "BRCC": {"opcode": "0x24", "desc": "Branch if carry cleared.", "format": "BRCC [const]"},
            "BRMI": {"opcode": "0x25", "desc": "Branch if minus.", "format": "BRMI [const]"},
            "BRPL": {"opcode": "0x26", "desc": "Branch if plus.", "format": "BRPL [const]"},
            "BREQ": {"opcode": "0x27", "desc": "Branch if equal.", "format": "BREQ [const]"},
            "BRNE": {"opcode": "0x28", "desc": "Branch if not equal.", "format": "BRNE [const]"},
            "BRVS": {"opcode": "0x29", "desc": "Branch if overflow set.", "format": "BRVS [const]"},
            "BRVC": {"opcode": "0x2a", "desc": "Branch if overflow cleared.", "format": "BRVC [const]"},
            "ST": {"opcode": "0x2b", "desc": "Stores the contents of register Rs to the memory address specified by register Rd.", "format": "ST Rd,Rs"},
            "LD": {"opcode": "0x2c", "desc": "Loads register Rd with the memory value at the address held in register Rs.", "format": "LD Rd,Rs"},
            "STS": {"opcode": "0x2d", "desc": "Stores the contents of register Rs to a memory location determined by a constant [const].", "format": "STS [const],Rs"},
            "STSs": {"opcode": "0x2e", "desc": "Stores the contents of register Rs to a memory location determined by a constant [const]. (0<=[const]<=15)", "format": "STSs [const],Rs"},
            "LDS": {"opcode": "0x2f", "desc": "Loads register Rd with the memory value at the address specified by the constant [const].", "format": "LDS Rd,[const]"},
            "LDSs": {"opcode": "0x30", "desc": "Loads register Rd with the memory value at the address specified by the constant [const]. (0<=[const]<=15)", "format": "LDSs Rd,[const]"},
            "STD": {"opcode": "0x31", "desc": "Stores data to a memory address calculated by adding a constant to the value in register Rd.", "format": "STD Rd+[const],Rs"},
            "LDD": {"opcode": "0x32", "desc": "Loads data from a memory address calculated by adding a constant to the value in register Rs.", "format": "LDD Rd,Rs+[const]"},
            "LDDd": {"opcode": "0x33", "desc": "Loads data from a memory address calculated by adding a constant to the value in register Rd (decreasing Rd).", "format": "LDDd Rd,[const]"},
            "BRLT": {"opcode": "0x34", "desc": "Branch if less than (signed).", "format": "BRLT [const]"},
            "BRGE": {"opcode": "0x35", "desc": "Branch if greater than or equal (signed).", "format": "BRGE [const]"},
            "BRLE": {"opcode": "0x36", "desc": "Branch if less than or equal (signed).", "format": "BRLE [const]"},
            "BRGT": {"opcode": "0x37", "desc": "Branch if greater than (signed).", "format": "BRGT [const]"},
            "OUT": {"opcode": "0x3e", "desc": "Writes the content of register Rs to io location given by [const].", "format": "OUT [const],Rs"},
            "OUTs": {"opcode": "0x3f", "desc": "Writes the content of register Rs to io location given by [const]. (0<=[const]<=15)", "format": "OUTs [const],Rs"},
            "OUTR": {"opcode": "0x40", "desc": "Writes the content of register Rs to the io location [Rd].", "format": "OUTR [Rd],Rs"},
            "IN": {"opcode": "0x41", "desc": "Reads the io location given by [const] and stores it in register Rd.", "format": "IN Rd,[const]"},
            "INs": {"opcode": "0x42", "desc": "Reads the io location given by [const] and stores it in register Rd. (0<=[const]<=15)", "format": "INs Rd,[const]"},
            "INR": {"opcode": "0x43", "desc": "Reads the io location given by (Rs) and stores it in register Rd.", "format": "INR Rd,[Rs]"},
            "BRK": {"opcode": "0x44", "desc": "Stops execution by stopping the simulator.", "format": "BRK"},
            "RETI": {"opcode": "0x45", "desc": "Return from Interrupt.", "format": "RETI"},
            
            # Macros
            "POP": {"desc": "Copy value from the stack to the given register, adds one to the stack pointer.", "format": "POP Rd", "type": "macro"},
            "RET": {"desc": "Jumps to the address which is stored on top of the stack. Decreases the stack pointer by 1+const. const is optional.", "format": "RET [const]", "type": "macro"},
            "CALL": {"desc": "Jumps to the given Address, stores the return address on the stack.", "format": "CALL [const]", "type": "macro"},
            "DEC": {"desc": "Decreases the given register by one.", "format": "DEC Rd", "type": "macro"},
            "LEAVE": {"desc": "Moves BP to SP and pops BP from the stack.", "format": "LEAVE", "type": "macro"},
            "LEAVEI": {"desc": "Pops R0 and the flags from the stack.", "format": "LEAVEI", "type": "macro"},
            "ENTER": {"desc": "Pushes BP on stack, copies SP to BP and reduces SP by the given constant.", "format": "ENTER [const]", "type": "macro"},
            "ENTERI": {"desc": "Pushes R0 and the flags to the stack.", "format": "ENTERI", "type": "macro"},
            "_SCALL": {"desc": "Jumps to the address given in const and stores the return address in the register RA. Before that RA ist pushed to the stack, and after the return RA is poped of the stack again.", "format": "_SCALL [const]", "type": "macro"},
            "PUSH": {"desc": "Copies the value in the given register to the stack, decreases the stack pointer by one.", "format": "PUSH Rs", "type": "macro"},
            "INC": {"desc": "Increases the given register by one.", "format": "INC Rd", "type": "macro"}
        }
        
        details = instruction_details.get(instruction.upper(), {"opcode": "N/A", "desc": "No details available."})
        
        html = f"""
        <h2>{instruction.upper()}</h2>
        """
        
        if details.get("type") == "macro":
            html += "<p><b>Type:</b> Macro</p>"
        else:
            html += f"<p><b>Opcode:</b> {details.get('opcode', 'N/A')}</p>"
            
        html += f"<p><b>Description:</b> {details.get('desc', 'No description available.')}</p>"
        
        if "format" in details:
            html += f"<p><b>Format:</b> {details['format']}</p>"
        
        self.details.setHtml(html)


class AssemblerGUI(QMainWindow):
    """Main window for the assembler application."""
    
    def __init__(self):
        super().__init__()
        
        self.setWindowTitle("Assembler IDE")
        self.setMinimumSize(1200, 800)
        
        # Create the main editor
        self.editor = AssemblerEditor(self)
        
        # Create the output console
        self.console = OutputConsole(self)
        
        # Create instruction reference widget
        self.instruction_ref = InstructionReferenceWidget(self)
        
        # Create splitters for layout
        self.main_splitter = QSplitter(Qt.Orientation.Vertical)
        self.main_splitter.addWidget(self.editor)
        self.main_splitter.addWidget(self.console)
        self.main_splitter.setSizes([600, 200])
        
        # Set central widget
        self.setCentralWidget(self.main_splitter)
        
        # Create dock for instruction reference
        self.ref_dock = QDockWidget("Instruction Reference", self)
        self.ref_dock.setWidget(self.instruction_ref)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.ref_dock)
        
        # Create menus and toolbars
        self.create_menus()
        self.create_toolbar()
        
        # Set up status bar
        self.statusBar().showMessage("Ready")
    
    def create_menus(self):
        """Create the application menus."""
        # File menu
        file_menu = self.menuBar().addMenu("&File")
        
        new_action = QAction("&New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)
        
        open_action = QAction("&Open...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Alt+F4")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = self.menuBar().addMenu("&Edit")
        
        undo_action = QAction("&Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.editor.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction("&Redo", self)
        redo_action.setShortcut("Ctrl+Y")
        redo_action.triggered.connect(self.editor.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        cut_action = QAction("Cu&t", self)
        cut_action.setShortcut("Ctrl+X")
        cut_action.triggered.connect(self.editor.cut)
        edit_menu.addAction(cut_action)
        
        copy_action = QAction("&Copy", self)
        copy_action.setShortcut("Ctrl+C")
        copy_action.triggered.connect(self.editor.copy)
        edit_menu.addAction(copy_action)
        
        paste_action = QAction("&Paste", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self.editor.paste)
        edit_menu.addAction(paste_action)
        
        # Build menu
        build_menu = self.menuBar().addMenu("&Build")
        
        assemble_action = QAction("&Assemble", self)
        assemble_action.setShortcut("F5")
        assemble_action.triggered.connect(self.assemble_current_file)
        build_menu.addAction(assemble_action)
        
        # View menu
        view_menu = self.menuBar().addMenu("&View")
        
        toggle_ref_action = QAction("Instruction &Reference", self)
        toggle_ref_action.setCheckable(True)
        toggle_ref_action.setChecked(True)
        toggle_ref_action.triggered.connect(self.toggle_reference)
        view_menu.addAction(toggle_ref_action)
    
    def create_toolbar(self):
        """Create the application toolbar."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Add file operations
        new_action = QAction("New", self)
        new_action.triggered.connect(self.new_file)
        toolbar.addAction(new_action)
        
        open_action = QAction("Open", self)
        open_action.triggered.connect(self.open_file)
        toolbar.addAction(open_action)
        
        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_file)
        toolbar.addAction(save_action)
        
        toolbar.addSeparator()
        
        # Add build operations
        assemble_action = QAction("Assemble", self)
        assemble_action.triggered.connect(self.assemble_current_file)
        toolbar.addAction(assemble_action)
        
        toolbar.addSeparator()
        
        # Add output options
        output_label = QLabel("Output:")
        toolbar.addWidget(output_label)
        
        self.output_hex_cb = QComboBox()
        self.output_hex_cb.addItems(["No output", "HEX only", "LST only", "MAP only", "All outputs"])
        self.output_hex_cb.setCurrentIndex(1)  # Default to HEX only
        toolbar.addWidget(self.output_hex_cb)
    
    def new_file(self):
        """Create a new file."""
        if self.maybe_save():
            self.editor.new_file()
            self.statusBar().showMessage("New file created")
    
    def open_file(self):
        """Open a file."""
        if self.maybe_save():
            if self.editor.open_file():
                self.statusBar().showMessage(f"Opened {self.editor.current_file}")
    
    def save_file(self):
        """Save the current file."""
        if self.editor.save_file():
            self.statusBar().showMessage(f"Saved {self.editor.current_file}")
    
    def save_file_as(self):
        """Save the file with a new name."""
        if self.editor.save_file_as():
            self.statusBar().showMessage(f"Saved as {self.editor.current_file}")
    
    def maybe_save(self):
        """Check if the current file needs to be saved before proceeding."""
        if not self.editor.modified:
            return True
        
        reply = QMessageBox.question(
            self, "Save Changes",
            "The document has been modified. Save changes?",
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Save:
            return self.editor.save_file()
        elif reply == QMessageBox.StandardButton.Cancel:
            return False
        
        return True
    
    def toggle_reference(self, checked):
        """Toggle the instruction reference dock."""
        if checked:
            self.ref_dock.show()
        else:
            self.ref_dock.hide()
    
    def assemble_current_file(self):
        """Assemble the current file."""
        if not self.editor.current_file and not self.save_file():
            return
        
        # Clear previous output
        self.console.clear_console()
        
        # Get output options
        output_option = self.output_hex_cb.currentIndex()
        gen_hex = output_option in [1, 4]
        gen_lst = output_option in [2, 4]
        gen_map = output_option in [3, 4]
        
        # Set up output filenames
        input_base = self.editor.current_file.rsplit('.', 1)[0]
        hex_file = f"{input_base}.hex" if gen_hex else None
        lst_file = f"{input_base}.lst" if gen_lst else None
        map_file = f"{input_base}.map" if gen_map else None
        
        # Try to assemble
        try:
            self.console.append_message(f"Assembling {self.editor.current_file}...", "blue")
            
            # Save current file first
            self.editor.save_file()
            
            # Assemble the file using the imported assembler code
            with open(self.editor.current_file, 'r', encoding='utf-8') as f:
                parser = Parser(f, base_file=self.editor.current_file)
                program = parser.parse_program()
                self.console.append_message("Parsing complete. Optimizing and linking...", "blue")
                program.optimize_and_link()
                self.console.append_message("Linking complete.", "blue")
            
            if hex_file:
                self.console.append_message(f"Writing hex file to {hex_file}...", "blue")
                with open(hex_file, 'w', encoding='utf-8') as f:
                    formatter = HexFormatter(f)
                    program.traverse(formatter)
                    formatter.finalize()  # Important for HexFormatter
            
            if lst_file:
                self.console.append_message(f"Writing listing file to {lst_file}...", "blue")
                with open(lst_file, 'w', encoding='utf-8') as f:
                    formatter = AsmFormatter(f)
                    program.traverse(formatter)

            if map_file:
                self.console.append_message(f"Not implemented", "blue")
            
            # Show success message
            self.console.append_message(f"Assembly successful!", "green")
            
        except (ExpressionException, ParserException, InstructionException) as e:
            # Handle assembler errors
            self.console.append_message(f"Error: {str(e)}", "red")
            
            # Try to extract line information
            if hasattr(e, 'lineno') and hasattr(e, 'filename'):
                self.console.append_message(f"  at line {e.lineno} in {e.filename}", "red")
                
                # Highlight the error in the editor if it's the current file
                if os.path.abspath(e.filename) == os.path.abspath(self.editor.current_file):
                    cursor = self.editor.textCursor()
                    doc = self.editor.document()
                    cursor.setPosition(doc.findBlockByLineNumber(e.lineno - 1).position())
                    self.editor.setTextCursor(cursor)
            
        except Exception as e:
            # Handle unexpected errors
            self.console.append_message(f"Unexpected error: {str(e)}", "red")
            self.console.append_message(traceback.format_exc(), "red")


def main():
    """Main application entry point."""
    app = QApplication(sys.argv)
    window = AssemblerGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
 
