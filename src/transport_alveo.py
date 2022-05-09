from transport_katcp import KatcpTransport
import katcp

class AlveoFunctionError(RuntimeError):
  """Not an Alveo function"""
  pass

#inherit from katcp transport for now (TODO)
class AlveoTransport(KatcpTransport):

  @staticmethod
  def test_host_type(host_ip, port, timeout=5):
    """
    Is this host_ip assigned to an Alveo?
    """
    #print("new alveo-test-host")
    try:
      board = katcp.CallbackClient(host=host_ip, port=port,
      timeout=timeout, auto_reconnect=False)
      board.setDaemon(True)
      board.start()
      connected = board.wait_connected(timeout)

      #TODO this read needs to be standardized with the final mem map
      #reply,informs = board.blocking_request(katcp.Message.request('alveo-read','0x28000' ),timeout=timeout)
      #reply,informs = board.blocking_request(katcp.Message.request('alveo-read','0x90004' ),timeout=timeout)
      reply,informs = board.blocking_request(katcp.Message.request('wordread','id' ),timeout=timeout)
      board.stop()

      #args = [(i.arguments[0], i.arguments[1]) for i in informs]
      #if args[0][1] == '0x74736574':
      #if args[0][1] == '0xDECADE05':
      if reply.arguments[1] == '0xdecade05':
        #print("Seems to be an ALVEO")   #TODO to be removed
        return True
      else:
        #print("Seems not to be an ALVEO")   #TODO to be removed
        return False

    except AttributeError:
      #print("alveo-error")
      raise RuntimeError("Please ensure that katcp-python >=v0.6.3 is being used")

    except Exception:
      #print("alveo-failed")
      return False


  def reset(self):
    """
    :return: reset the ALVEO
    """
    reply, _ = self.katcprequest(name='alveo-reset', request_timeout=self._timeout)
    return reply.arguments[0] == 'ok'


  def upload_to_ram_and_program(self, filename, timeout=120):  #TODO this timeout may be too short for large images
    self.upload_to_flash(filename)
    self.program(filename)

    reply, _ = self.katcprequest(
    name='alveo-program', request_timeout=timeout, require_ok=True)
    #delete regardless of returned status, then check status...
    self._delete_bof(filename)
    if reply.arguments[0] != 'ok':
      raise RuntimeError('%s: could not program alveo' % self.host)



  def check_phy_counter(self):
    raise AlveoFunctionError("Not an Alveo function")
  pass
