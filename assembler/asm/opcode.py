import sys
from enum import Enum, auto
from typing import Optional, Dict, Tuple, Callable, List, TextIO
from dataclasses import dataclass

# Forward declaration for type hints
class MnemonicArguments: pass

# --- Control Signal Enums (mimicking Java structure) ---
class ReadRam(Enum): No = 0; Yes = 1
class ReadIO(Enum): No = 0; Yes = 1
class WriteRam(Enum): No = 0; Yes = 1
class WriteIO(Enum): No = 0; Yes = 1
class Break(Enum): No = 0; Yes = 1
class SourceToAluA(Enum): No = 0; Yes = 1
class Branch(Enum): No = 0; BRC = 1; BRZ = 2; BRN = 3; uncond = 4; BRNC = 5; BRNZ = 6; BRNN = 7
class ALUBSel(Enum): Source = 0; Rom = 1; ImReg = 2; Zero = 3; res = 4; instrSource = 5; instrSourceAndDest = 6; instrDest = 7
class ALUToBus(Enum): No = 0; Yes = 1
class SrcToBus(Enum): No = 0; Yes = 1
class ImmExtMode(Enum): extend = 0; res = 1; src0 = 2; dest0 = 3
class ALUCmd(Enum):
    PassInB = 0; ADD = 1; SUB = 2; AND = 3; OR = 4; XOR = 5; NOT = 6; NEG = 7
    LSL = 8; LSR = 9; ASR = 10; SWAP = 11; SWAPN = 12; MUL = 13; res4 = 14; res5 = 15
    res6 = 16; ADC = 17; SBC = 18; res7 = 19; res8 = 20; res9 = 21; res10 = 22; res11 = 23
    ROL = 24; ROR = 25 # Up to 25 requires 5 bits
class EnRegWrite(Enum): No = 0; Yes = 1
class StorePC(Enum): No = 0; Yes = 1
class JmpAbs(Enum): No = 0; Yes = 1
class RetI(Enum): No = 0; Yes = 1
class StoreFlags(Enum): No = 0; Yes = 1

@dataclass(frozen=True) # Use dataclass for Flags, make it immutable
class Flags:
    rr: ReadRam = ReadRam.No
    wr: WriteRam = WriteRam.No
    br: Branch = Branch.No
    alu_b_sel: ALUBSel = ALUBSel.Source
    imm_ext_mode: ImmExtMode = ImmExtMode.extend
    alu_to_bus: ALUToBus = ALUToBus.No
    src_to_bus: SrcToBus = SrcToBus.No
    alu_cmd: ALUCmd = ALUCmd.PassInB
    en_reg_write: EnRegWrite = EnRegWrite.No
    store_pc: StorePC = StorePC.No
    source_to_alu_a: SourceToAluA = SourceToAluA.No
    jmp_abs: JmpAbs = JmpAbs.No
    ret_i: RetI = RetI.No
    wio: WriteIO = WriteIO.No
    rio: ReadIO = ReadIO.No
    brk: Break = Break.No
    str_flags: StoreFlags = StoreFlags.No

# --- Control Word Builder Helper ---
class ControlWordBuilder:
    def __init__(self, out: bool = False):
        self._out = out
        self._pos = 0
        self._control_word = 0
        self._sb: List[str] = []

    def add(self, e: Enum) -> 'ControlWordBuilder':
        enum_type = type(e)
        num_constants = len(enum_type)
        # Calculate width based on number of enum members
        if num_constants <= 2:
            width = 1
        elif num_constants <= 4:
            width = 2
        elif num_constants <= 8:
            width = 3
        elif num_constants <= 16:
             width = 4
        elif num_constants <= 32:
             width = 5 # ALUCmd needs 5 bits (26 values)
        else:
            raise ValueError(f"Unsupported enum size: {enum_type.__name__} has {num_constants} members")

        self._control_word |= (e.value << self._pos)

        if self._out:
            pos_str = f"{self._pos}" if width == 1 else f"{self._pos}-{self._pos + width - 1}"
            self._sb.append(f"{pos_str}\t:{enum_type.__name__}")
            print(f"{pos_str}\t:{enum_type.__name__}", file=sys.stderr) # Print to stderr for debug/info

        self._pos += width
        return self

    def get_control_word(self) -> int:
        if self._sb:
             print("Splitter: " + ",".join([s.split('\t:')[0] for s in self._sb]), file=sys.stderr)
        # print(f"Total control word bits: {self._pos}") # Debug
        return self._control_word

# Opcode Definition needs to import MnemonicArguments later
_mnemonics = {} # Placeholder, will be populated after MnemonicArguments is defined

class Opcode(Enum):
    # Assign explicit integer values matching the original order (0-based)
    NOP = 0, "Does nothing.", lambda: _mnemonics['NOTHING'], Flags()
    MOV = 1, "Move the content of Rs to register Rd.", lambda: _mnemonics['DEST_SOURCE'], Flags(src_to_bus=SrcToBus.Yes, en_reg_write=EnRegWrite.Yes)
    ADD = 2, "Adds the content of register Rs to register Rd without carry.", lambda: _mnemonics['DEST_SOURCE'], Flags(alu_cmd=ALUCmd.ADD, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes)
    ADC = 3, "Adds the content of register Rs to register Rd with carry.", lambda: _mnemonics['DEST_SOURCE'], Flags(alu_cmd=ALUCmd.ADC, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes)
    SUB = 4, "Subtracts the content of register Rs from register Rd without carry.", lambda: _mnemonics['DEST_SOURCE'], Flags(alu_cmd=ALUCmd.SUB, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes)
    SBC = 5, "Subtracts the content of register Rs from register Rd with carry.", lambda: _mnemonics['DEST_SOURCE'], Flags(alu_cmd=ALUCmd.SBC, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes)
    AND = 6, "Stores Rs and Rd in register Rd.", lambda: _mnemonics['DEST_SOURCE'], Flags(alu_cmd=ALUCmd.AND, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes)
    OR = 7, "Stores Rs or Rd in register Rd.", lambda: _mnemonics['DEST_SOURCE'], Flags(alu_cmd=ALUCmd.OR, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes)
    EOR = 8, "Stores Rs xor Rd in register Rd.", lambda: _mnemonics['DEST_SOURCE'], Flags(alu_cmd=ALUCmd.XOR, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes)
    LDI = 9, "Loads Register Rd with the constant value [const].", lambda: _mnemonics['DEST_CONST'], Flags(alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes, imm_ext_mode=ImmExtMode.src0, alu_b_sel=ALUBSel.ImReg)
    LDIs = 10, "Loads Register Rd with the constant value [const].", lambda: _mnemonics['DEST_CONST'], Flags(alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes, alu_b_sel=ALUBSel.instrSource)
    ADDI = 11, "Adds the constant [const] to register Rd without carry.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.ADD, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes, imm_ext_mode=ImmExtMode.src0, alu_b_sel=ALUBSel.ImReg)
    ADDIs = 12, "Adds the constant [const] to register Rd without carry.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.ADD, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes, alu_b_sel=ALUBSel.instrSource)
    ADCI = 13, "Adds the constant [const] to register Rd with carry.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.ADC, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes, imm_ext_mode=ImmExtMode.src0, alu_b_sel=ALUBSel.ImReg)
    ADCIs = 14, "Adds the constant [const] to register Rd with carry.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.ADC, alu_to_bus=ALUToBus.Yes, str_flags=StoreFlags.Yes, en_reg_write=EnRegWrite.Yes, alu_b_sel=ALUBSel.instrSource)
    SUBI = 15, "Subtracts a constant [const] from register Rd without carry.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.SUB, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes, imm_ext_mode=ImmExtMode.src0, alu_b_sel=ALUBSel.ImReg)
    SUBIs = 16, "Subtracts a constant [const] from register Rd without carry.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.SUB, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes, alu_b_sel=ALUBSel.instrSource)
    SBCI = 17, "Subtracts a constant [const] from register Rd with carry.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.SBC, alu_to_bus=ALUToBus.Yes, str_flags=StoreFlags.Yes, en_reg_write=EnRegWrite.Yes, imm_ext_mode=ImmExtMode.src0, alu_b_sel=ALUBSel.ImReg)
    SBCIs = 18, "Subtracts a constant [const] from register Rd with carry.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.SBC, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes, alu_b_sel=ALUBSel.instrSource)
    NEG = 19, "Stores the two's complement of Rd in register Rd.", lambda: _mnemonics['DEST'], Flags(alu_cmd=ALUCmd.NEG, str_flags=StoreFlags.No, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes)
    ANDI = 20, "Stores Rd and [const] in register Rd.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.AND, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes, imm_ext_mode=ImmExtMode.src0, alu_b_sel=ALUBSel.ImReg)
    ANDIs = 21, "Stores Rd and [const] in register Rd.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.AND, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes, alu_b_sel=ALUBSel.instrSource)
    ORI = 22, "Stores Rd or [const] in register Rd.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.OR, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes, imm_ext_mode=ImmExtMode.src0, alu_b_sel=ALUBSel.ImReg)
    ORIs = 23, "Stores Rd or [const] in register Rd.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.OR, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes, alu_b_sel=ALUBSel.instrSource)
    EORI = 24, "Stores Rd xor [const] in register Rd.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.XOR, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes, imm_ext_mode=ImmExtMode.src0, alu_b_sel=ALUBSel.ImReg)
    EORIs = 25, "Stores Rd xor [const] in register Rd.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.XOR, alu_to_bus=ALUToBus.Yes, str_flags=StoreFlags.Yes, en_reg_write=EnRegWrite.Yes, alu_b_sel=ALUBSel.instrSource)
    NOT = 26, "Stores not Rd in register Rd.", lambda: _mnemonics['DEST'], Flags(alu_cmd=ALUCmd.NOT, str_flags=StoreFlags.No, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes)
    MUL = 27, "Multiplies the content of register Rs with register Rd and stores result in Rd.", lambda: _mnemonics['DEST_SOURCE'], Flags(alu_cmd=ALUCmd.MUL, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes)
    MULI = 28, "Multiplies the constant [const] with register Rd and stores result in Rd.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.MUL, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes, imm_ext_mode=ImmExtMode.src0, alu_b_sel=ALUBSel.ImReg)
    MULIs = 29, "Multiplies the constant [const] with register Rd and stores result in Rd.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.MUL, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes, alu_b_sel=ALUBSel.instrSource)
    CMP = 30, "Subtracts the content of register Rs from register Rd without carry, does not store the result.", lambda: _mnemonics['DEST_SOURCE'], Flags(str_flags=StoreFlags.Yes, alu_cmd=ALUCmd.SUB)
    CPC = 31, "Subtracts the content of register Rs from register Rd with carry, does not store the result.", lambda: _mnemonics['DEST_SOURCE'], Flags(str_flags=StoreFlags.Yes, alu_cmd=ALUCmd.SBC)
    CPI = 32, "Subtracts a constant [const] from register Rd without carry, does not store the result.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.SUB, str_flags=StoreFlags.Yes, imm_ext_mode=ImmExtMode.src0, alu_b_sel=ALUBSel.ImReg)
    CPIs = 33, "Subtracts a constant [const] from register Rd without carry, does not store the result.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.SUB, str_flags=StoreFlags.Yes, alu_b_sel=ALUBSel.instrSource)
    CPCI = 34, "Subtracts a constant [const] from register Rd with carry, does not store the result.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.SBC, str_flags=StoreFlags.Yes, imm_ext_mode=ImmExtMode.src0, alu_b_sel=ALUBSel.ImReg)
    CPCIs = 35, "Subtracts a constant [const] from register Rd with carry, does not store the result.", lambda: _mnemonics['DEST_CONST'], Flags(alu_cmd=ALUCmd.SBC, str_flags=StoreFlags.Yes, alu_b_sel=ALUBSel.instrSource)
    LSL = 36, "Shifts register Rd by one bit to the left. A zero bit is filled in and the highest bit is moved to the carry bit.", lambda: _mnemonics['DEST'], Flags(alu_cmd=ALUCmd.LSL, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes)
    LSR = 37, "Shifts register Rd by one bit to the right. A zero bit is filled in and the lowest bit is moved to the carry bit.", lambda: _mnemonics['DEST'], Flags(alu_cmd=ALUCmd.LSR, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes)
    ROL = 38, "Shifts register Rd by one bit to the left. The carry bit is filled in and the highest bit is moved to the carry bit.", lambda: _mnemonics['DEST'], Flags(alu_cmd=ALUCmd.ROL, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes)
    ROR = 39, "Shifts register Rd by one bit to the right. The carry bit is filled in and the lowest bit is moved to the carry bit.", lambda: _mnemonics['DEST'], Flags(alu_cmd=ALUCmd.ROR, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes)
    ASR = 40, "Shifts register Rd by one bit to the right. The MSB remains unchanged and the lowest bit is moved to the carry bit.", lambda: _mnemonics['DEST'], Flags(alu_cmd=ALUCmd.ASR, str_flags=StoreFlags.Yes, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes)
    SWAP = 41, "Swaps the high and low byte in register Rd.", lambda: _mnemonics['DEST'], Flags(alu_cmd=ALUCmd.SWAP, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes)
    SWAPN = 42, "Swaps the high and low nibbles of both bytes in register Rd.", lambda: _mnemonics['DEST'], Flags(alu_cmd=ALUCmd.SWAPN, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes)
    ST = 43, "Stores the content of register Rs to the memory at the address [Rd].", lambda: _mnemonics['BDEST_SOURCE'], Flags(wr=WriteRam.Yes, src_to_bus=SrcToBus.Yes, alu_b_sel=ALUBSel.Zero, alu_cmd=ALUCmd.ADD)
    LD = 44, "Loads the value at memory address [Rs] to register Rd.", lambda: _mnemonics['DEST_BSOURCE'], Flags(rr=ReadRam.Yes, alu_b_sel=ALUBSel.Zero, alu_cmd=ALUCmd.ADD, source_to_alu_a=SourceToAluA.Yes, en_reg_write=EnRegWrite.Yes)
    STS = 45, "Stores the content of register Rs to memory at the location given by [const].", lambda: _mnemonics['CONST_SOURCE'], Flags(wr=WriteRam.Yes, src_to_bus=SrcToBus.Yes, imm_ext_mode=ImmExtMode.dest0, alu_b_sel=ALUBSel.ImReg)
    STSs = 46, "Stores the content of register Rs to memory at the location given by [const].", lambda: _mnemonics['CONST_SOURCE'], Flags(wr=WriteRam.Yes, src_to_bus=SrcToBus.Yes, alu_b_sel=ALUBSel.instrDest)
    LDS = 47, "Loads the memory value at the location given by [const] to register Rd.", lambda: _mnemonics['DEST_CONST'], Flags(rr=ReadRam.Yes, imm_ext_mode=ImmExtMode.src0, alu_b_sel=ALUBSel.ImReg, en_reg_write=EnRegWrite.Yes)
    LDSs = 48, "Loads the memory value at the location given by [const] to register Rd.", lambda: _mnemonics['DEST_CONST'], Flags(rr=ReadRam.Yes, alu_b_sel=ALUBSel.instrSource, en_reg_write=EnRegWrite.Yes)
    STD = 49, "Stores the content of register Rs to the memory at the address (Rd+[const]).", lambda: _mnemonics['BDEST_BCONST_SOURCE'], Flags(wr=WriteRam.Yes, src_to_bus=SrcToBus.Yes, imm_ext_mode=ImmExtMode.extend, alu_b_sel=ALUBSel.ImReg, alu_cmd=ALUCmd.ADD)
    LDD = 50, "Loads the value at memory address (Rs+[const]) to register Rd.", lambda: _mnemonics['DEST_BSOURCE_BCONST'], Flags(rr=ReadRam.Yes, imm_ext_mode=ImmExtMode.extend, alu_b_sel=ALUBSel.ImReg, alu_cmd=ALUCmd.ADD, en_reg_write=EnRegWrite.Yes, source_to_alu_a=SourceToAluA.Yes)
    LPM = 51, "Loads the value at program address [Rs] to register Rd. In a single cycle machine this requires dual ported program memory.", lambda: _mnemonics['DEST_BSOURCE'], Flags(alu_b_sel=ALUBSel.Rom, alu_cmd=ALUCmd.PassInB, alu_to_bus=ALUToBus.Yes, en_reg_write=EnRegWrite.Yes)
    BRCS = 52, "Jumps to the address given by [const] if carry flag is set.", lambda: _mnemonics['CONST'], Flags(alu_b_sel=ALUBSel.instrSourceAndDest, br=Branch.BRC)
    BREQ = 53, "Jumps to the address given by [const] if zero flag is set.", lambda: _mnemonics['CONST'], Flags(alu_b_sel=ALUBSel.instrSourceAndDest, br=Branch.BRZ)
    BRMI = 54, "Jumps to the address given by [const] if negative flag is set.", lambda: _mnemonics['CONST'], Flags(alu_b_sel=ALUBSel.instrSourceAndDest, br=Branch.BRN)
    BRCC = 55, "Jumps to the address given by [const] if carry flag is clear.", lambda: _mnemonics['CONST'], Flags(alu_b_sel=ALUBSel.instrSourceAndDest, br=Branch.BRNC)
    BRNE = 56, "Jumps to the address given by [const] if zero flag is clear.", lambda: _mnemonics['CONST'], Flags(alu_b_sel=ALUBSel.instrSourceAndDest, br=Branch.BRNZ)
    BRPL = 57, "Jumps to the address given by [const] if negative flag is clear.", lambda: _mnemonics['CONST'], Flags(alu_b_sel=ALUBSel.instrSourceAndDest, br=Branch.BRNN)
    RCALL = 58, "Jumps to the address given by [const], the return address is stored in register Rd.", lambda: _mnemonics['DEST_CONST'], Flags(imm_ext_mode=ImmExtMode.src0, alu_b_sel=ALUBSel.ImReg, store_pc=StorePC.Yes, en_reg_write=EnRegWrite.Yes, jmp_abs=JmpAbs.Yes)
    RRET = 59, "Jumps to the address given by register Rs.", lambda: _mnemonics['SOURCE'], Flags(jmp_abs=JmpAbs.Yes) # Note: RRET uses Rs as address source, but doesn't fit standard ALU path well. Control unit handles this.
    JMP = 60, "Jumps to the address given by [const].", lambda: _mnemonics['CONST'], Flags(imm_ext_mode=ImmExtMode.src0, alu_b_sel=ALUBSel.ImReg, jmp_abs=JmpAbs.Yes)
    JMPs = 61, "Jumps to the address given by [const].", lambda: _mnemonics['CONST'], Flags(alu_b_sel=ALUBSel.instrSourceAndDest, br=Branch.uncond)
    OUT = 62, "Writes the content of register Rs to io location given by [const].", lambda: _mnemonics['CONST_SOURCE'], Flags(imm_ext_mode=ImmExtMode.dest0, alu_b_sel=ALUBSel.ImReg, src_to_bus=SrcToBus.Yes, wio=WriteIO.Yes)
    OUTs = 63, "Writes the content of register Rs to io location given by [const].", lambda: _mnemonics['CONST_SOURCE'], Flags(alu_b_sel=ALUBSel.instrDest, src_to_bus=SrcToBus.Yes, wio=WriteIO.Yes)
    OUTR = 64, "Writes the content of register Rs to the io location [Rd].", lambda: _mnemonics['BDEST_SOURCE'], Flags(alu_cmd=ALUCmd.ADD, alu_b_sel=ALUBSel.Zero, src_to_bus=SrcToBus.Yes, wio=WriteIO.Yes)
    IN = 65, "Reads the io location given by [const] and stores it in register Rd.", lambda: _mnemonics['DEST_CONST'], Flags(imm_ext_mode=ImmExtMode.src0, alu_b_sel=ALUBSel.ImReg, en_reg_write=EnRegWrite.Yes, source_to_alu_a=SourceToAluA.Yes, rio=ReadIO.Yes) # SourceToAluA might be wrong here, depends on how IO read path works. Assuming data bus -> reg.
    INs = 66, "Reads the io location given by [const] and stores it in register Rd.", lambda: _mnemonics['DEST_CONST'], Flags(alu_b_sel=ALUBSel.instrSource, en_reg_write=EnRegWrite.Yes, source_to_alu_a=SourceToAluA.Yes, rio=ReadIO.Yes) # Assuming ReadIO puts data on bus
    INR = 67, "Reads the io location given by (Rs) and stores it in register Rd.", lambda: _mnemonics['DEST_BSOURCE'], Flags(alu_b_sel=ALUBSel.Zero, alu_cmd=ALUCmd.ADD, en_reg_write=EnRegWrite.Yes, source_to_alu_a=SourceToAluA.Yes, rio=ReadIO.Yes) # Address from Rs -> ALU -> AddrBus, ReadIO puts data on bus
    BRK = 68, "Stops execution by stopping the simulator.", lambda: _mnemonics['NOTHING'], Flags(brk=Break.Yes)
    RETI = 69, "Return from Interrupt.", lambda: _mnemonics['NOTHING'], Flags(jmp_abs=JmpAbs.Yes, ret_i=RetI.Yes) # RETI needs special handling in control unit/sequencer

    # Store the original tuple value for potential debugging if needed
    _raw_value = None

    def __new__(cls, value, desc='', factory= lambda: _mnemonics['NOTHING'], flgs=Flags()):
        member = object.__new__(cls)
        member._value_ = value
        member._raw_value = (value, desc, factory, flgs)
        return member

    def __init__(self, value, desc='', factory= lambda: _mnemonics['NOTHING'], flgs=Flags()):
        _, desc, factory, flgs = self._raw_value
        self._description = self._add_const_limit(desc, flgs.alu_b_sel)
        self._arg_factory = factory
        self._flags = flgs
        self._arguments: Optional[MnemonicArguments] = None

    @property
    def description(self) -> str:
        return self._description

    @property
    def flags(self) -> Flags:
         return self._flags

    @property
    def arguments(self) -> MnemonicArguments:
        # Lazy initialization of arguments
        if self._arguments is None:
             # Need to import MnemonicArguments here to avoid circular dependency at module level
             from .mnemonic_arguments import MnemonicArguments, MNEMONIC_ARG_LOOKUP
             global _mnemonics # Allow modification of the global placeholder
             _mnemonics = MNEMONIC_ARG_LOOKUP # Populate the lookup now
             self._arguments = self._arg_factory()
        return self._arguments

    def _add_const_limit(self, description: str, alu_b_sel: ALUBSel) -> str:
        if alu_b_sel == ALUBSel.instrDest or alu_b_sel == ALUBSel.instrSource:
            return description + " (0<=[const]<=15)"
        elif alu_b_sel == ALUBSel.instrSourceAndDest:
            return description + " (-128<=[const]<=127)"
        else:
            return description

    def create_control_word(self, out: bool = False) -> int:
        f = self._flags
        return (ControlWordBuilder(out)
                .add(f.alu_b_sel)
                .add(f.src_to_bus)
                .add(f.alu_cmd)
                .add(f.en_reg_write)
                .add(f.str_flags)
                .add(f.alu_to_bus)
                .add(f.imm_ext_mode)
                .add(f.br)
                .add(f.source_to_alu_a)
                .add(f.rr)
                .add(f.wr)
                .add(f.jmp_abs)
                .add(f.wio)
                .add(f.rio)
                .add(f.store_pc)
                .add(f.brk)
                .add(f.ret_i)
                .get_control_word()
               )

    @property
    def alu_b_sel(self) -> ALUBSel: return self._flags.alu_b_sel
    @property
    def alu_to_bus(self) -> ALUToBus: return self._flags.alu_to_bus
    @property
    def src_to_bus(self) -> SrcToBus: return self._flags.src_to_bus
    @property
    def read_ram(self) -> ReadRam: return self._flags.rr
    @property
    def write_ram(self) -> WriteRam: return self._flags.wr
    @property
    def read_io(self) -> ReadIO: return self._flags.rio
    @property
    def write_io(self) -> WriteIO: return self._flags.wio
    @property
    def store_pc(self) -> StorePC: return self._flags.store_pc
    @property
    def en_reg_write(self) -> EnRegWrite: return self._flags.en_reg_write
    @property
    def imm_ext_mode(self) -> ImmExtMode: return self._flags.imm_ext_mode

    @classmethod
    def parse_str(cls, name: str) -> Optional['Opcode']:
        try:
            return cls[name.upper()]
        except KeyError:
            return None

    @staticmethod
    def write_control_words(out: TextIO):
        print("v2.0 raw", file=out)
        for oc in Opcode:
            if oc == Opcode._raw_value:
                continue
            print(f"{oc.create_control_word(False):x}", file=out)

    def __str__(self) -> str:
        # Access arguments property to ensure it's initialized
        args_str = str(self.arguments) if self.arguments else "<args_uninitialized>"
        return f"{self.name} {args_str}\n\t{self.description}"

