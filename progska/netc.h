#ifndef NETC_H_
#define NETC_H_

#ifdef __cplusplus
extern "C" {
#endif

#define NETC_VERBOSE_ERRORS  0x01
#define NETC_VERBOSE_STATS   0x02
#define NETC_ASYNC           0x04
#define NETC_TCP_KEEP_ALIVE  0x08
#define NETC_AUTO_PORT       0x10

#define NETC_DEFAULT_PORT    7147

#include <sys/types.h>
#include <sys/socket.h>

int net_connect(char *name, int port, int flags);
int net_listen(char *name, int port, int flags);
int net_address(struct sockaddr *sa, char *name, int port, int flags);
unsigned int net_port_fixup(unsigned int port);

#ifdef __cplusplus
}
#endif

#endif
