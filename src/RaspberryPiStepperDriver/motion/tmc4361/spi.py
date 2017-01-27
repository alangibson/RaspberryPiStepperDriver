import logging
import spidev
from RaspberryPiStepperDriver import tobin, set_bit, unset_bit
from RaspberryPiStepperDriver.motion.tmc4361 import registers
from RaspberryPiStepperDriver.activators import spi as activator_spi

log = logging.getLogger(__name__)

class SPI(activator_spi.SPI):
  
  def writeRegister(self, the_register, datagram):
    """
    Arguments:
    unsigned const char cs_squirrel
    unsigned const char the_register
    unsigned const long datagram
    """
    self.sendRegister(the_register | registers.WRITE_MASK, datagram)

  def readRegister(self, the_register):
    """
    Arguments:
    unsigned const char cs_squirrel
    unsigned const char the_register

    Returns: (unsigned long)
    """
    self.sendRegister(the_register, 0)
    result = self.sendRegister(the_register & registers.READ_MASK, 0)
    return result

  def sendRegister(self, the_register, datagram):
    """
    Arguments:
    (unsigned const char) motor_nr
    (unsigned const char) the_register
    (unsigned const long) datagram

    Returns: (unsigned long)
    """
    # "Whenever data is read from or written to the TMC4361A, the first eight
    # bits that are delivered back contain the SPI status SPI_STATUS that consists of
    # eight user-selected event bits. The selection of these bits are explained in
    # chapter 5.2"
    # the first value is ignored
    # unsigned char spi_status
    # spi_status = self.transfer([the_register])
    # print('spi_status:', spi_status)
    message = [
      the_register,
      (datagram >> 24) & 0xff,
      (datagram >> 16) & 0xff,
      (datagram >>  8) & 0xff,
      (datagram) & 0xff
    ]

    i_datagram = self.transfer(message)

    return i_datagram
