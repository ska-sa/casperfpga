/* GPLed code taken from shore:lib/net-connect.c */

#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <netdb.h>
#include <fcntl.h>
#include <errno.h>
#include <sysexits.h>

#include <sys/socket.h>
#include <sys/types.h>

#include <arpa/inet.h>
#include <netinet/in.h>
#include <netinet/tcp.h>

#include "netc.h"

unsigned int net_port_fixup(unsigned int port)
{
  if(port <= 0xffff){
    return port;
  }

  return (port % (0xffff - 1024)) + 1024;
}

int net_address(struct sockaddr *sa, char *name, int port, int flags)
{
  struct hostent *he;
  struct sockaddr_in *sai;
  char *ptr, *host, *copy, *end;
  int p, t, result;

  if(sa == NULL){
    return -1;
  }

  sai = (struct sockaddr_in *) sa;

  p = port;

  if(name == NULL){
    return -1;
  }

  copy = strdup(name);
  if(copy == NULL){
    if(flags & NETC_VERBOSE_ERRORS){ 
      fprintf(stderr, "address: internal allocation failure\n");
    }
    return -1;
  }

  result = 0;

  ptr = strchr(copy, ':');
  if(ptr){
    p = atoi(ptr + 1);
    if(ptr == copy){
      host = NULL;
    } else {
      host = copy;
      ptr[0] = '\0';
    }
  } else {
    ptr = strchr(copy, '.');
    if(ptr){
      host = copy;
    } else {
      t = strtoul(copy, &end, 10);
      if(end[0] == '\0'){
        p = t;
        host = NULL;
      } else {
        host = copy;
      }
    }
  }

  /* now we have a port, if there ever was one */

  if(host){
    if(inet_aton(host, &(sai->sin_addr)) == 0){
      he = gethostbyname(host);
      if((he == NULL) || (he->h_addrtype != AF_INET)){
        if(flags & NETC_VERBOSE_ERRORS){ 
          fprintf(stderr, "address: unable to resolve %s to ipv4 address\n", host);
        }
        result = (-1);
      } else {
        sai->sin_addr = *(struct in_addr *) he->h_addr;
      }
    }
  } else {
    result = 1;
  }

  free(copy);

  if(p > 0){
    if(p > 0xffff){
      if(flags & NETC_VERBOSE_ERRORS){ 
        fprintf(stderr, "address: port %d unreasonably large\n", p);
      }
      result = (-1);
    } else {
      sai->sin_port = htons(p);
    }
  } else {
    if(result == 0){
      result = 1;
    }
  }

  sai->sin_family = AF_INET;

  return result;
}

int net_connect(char *name, int port, int flags)
{
  /* WARNING: this function may call resolvers, and blocks for those */
  /* WARNING: uses ipv4 API */

  int p, len, fd, se, option;
  char *ptr, *host;
  struct hostent *he;
  struct sockaddr_in sa;
#ifndef SOCK_NONBLOCK
  long opts;
#endif

  p = NETC_DEFAULT_PORT;

  ptr = strchr(name, ':');
  if(ptr){
    p = atoi(ptr + 1);
  }

  if(port){
    p = port;
  }

  if(p == 0){
    if(flags & NETC_VERBOSE_ERRORS) fprintf(stderr, "connect: unable to acquire a port number\n");
    errno = EINVAL;
    return -2;
  }

  if((name[0] == '\0') || (name[0] == ':')){
#ifdef INADDR_LOOPBACK
    sa.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
#else
    if(flags & NETC_VERBOSE_ERRORS) fprintf(stderr, "connect: no destination address given\n");
    errno = EINVAL;
    return -2;
#endif
  } else {
    host = strdup(name);
    if(host == NULL){
      if(flags & NETC_VERBOSE_ERRORS) fprintf(stderr, "connect: unable to duplicate string\n");
      errno = ENOMEM;
      return -1;
    }

    ptr = strchr(host, ':');
    if(ptr){
      ptr[0] = '\0';
    }

    if(inet_aton(host, &(sa.sin_addr)) == 0){
      he = gethostbyname(host);
      if((he == NULL) || (he->h_addrtype != AF_INET)){
        if(flags & NETC_VERBOSE_ERRORS) fprintf(stderr, "connect: unable to map %s to ipv4 address\n", host);
        free(host);
        errno = EINVAL;
        return -1;
      }

      sa.sin_addr = *(struct in_addr *) he->h_addr;
    }

    free(host);
  }

  sa.sin_port = htons(p);
  sa.sin_family = AF_INET;

  if(flags & NETC_ASYNC){
#ifdef SOCK_NONBLOCK
    fd = socket(AF_INET, SOCK_STREAM | SOCK_NONBLOCK, 0);
#else
    fd = socket(AF_INET, SOCK_STREAM, 0);
    opts = fcntl(fd, F_GETFL, NULL);
    if(opts >= 0){
      opts = fcntl(fd, F_SETFL, opts | O_NONBLOCK);
    }
#endif
  } else {
    fd = socket(AF_INET, SOCK_STREAM, 0);
  }
  if(fd < 0){
    if(flags & NETC_VERBOSE_ERRORS){
      se = errno;
      fprintf(stderr, "connect: unable to allocate socket: %s\n", strerror(errno));
      errno = se;
    }
    return -1;
  }
   
  if(flags & NETC_VERBOSE_STATS){
    ptr = inet_ntoa(sa.sin_addr);
    fprintf(stderr, "connect: connecting to %s:%u\n", ptr, p);
  }
  
  if(flags & NETC_TCP_KEEP_ALIVE){
    option = 1;
    if (setsockopt(fd, SOL_SOCKET, SO_KEEPALIVE, &option, sizeof(option)) < 0){
      fprintf(stderr,"connect: cannot set keepalive socket option\n");
      return -1;
    }


    #ifdef __APPLE__
      #ifdef TCP_KEEPIDLE
      option = 10;
      if (setsockopt(fd, IPPROTO_TCP, TCP_KEEPIDLE, &option, sizeof(option)) < 0){
        fprintf(stderr,"connect: cannot set keepalive socket option\n");
        return -1;
      }
      #endif
      #ifdef TCP_KEEPINTVL
      option = 10;
      if (setsockopt(fd, IPPROTO_TCP, TCP_KEEPINTVL, &option, sizeof(option)) < 0){
        fprintf(stderr,"connect: cannot set keepalive socket option\n");
        return -1;
      }
      #endif
      #ifdef TCP_KEEPCNT
      option = 3;
      if (setsockopt(fd, IPPROTO_TCP, TCP_KEEPCNT, &option, sizeof(option)) < 0){
        fprintf(stderr,"connect: cannot set keepalive socket option\n");
        return -1;
      }
      #endif
  #elif __linux__
    #ifdef TCP_KEEPIDLE
    option = 10;
    if (setsockopt(fd, SOL_TCP, TCP_KEEPIDLE, &option, sizeof(option)) < 0){
      fprintf(stderr,"connect: cannot set keepalive socket option\n");
      return -1;
    }
    #endif
    #ifdef TCP_KEEPINTVL
    option = 10;
    if (setsockopt(fd, SOL_TCP, TCP_KEEPINTVL, &option, sizeof(option)) < 0){
      fprintf(stderr,"connect: cannot set keepalive socket option\n");
      return -1;
    }
    #endif
    #ifdef TCP_KEEPCNT
    option = 3;
    if (setsockopt(fd, SOL_TCP, TCP_KEEPCNT, &option, sizeof(option)) < 0){
      fprintf(stderr,"connect: cannot set keepalive socket option\n");
      return -1;
    }
    #endif

  #endif
  }

  len = sizeof(struct sockaddr_in);

  if(connect(fd, (struct sockaddr *)(&sa), len)){
    if(flags & NETC_ASYNC){
      if(errno == EINPROGRESS){
        return fd;
      }
    }
    se = errno;
    close(fd);
    if(flags & NETC_VERBOSE_ERRORS){
      ptr = inet_ntoa(sa.sin_addr);
      fprintf(stderr, "connect: connect to %s:%u failed: %s\n", ptr, p, strerror(errno));
    }
    errno = se;
    return -1;
  }

  if(flags & NETC_VERBOSE_STATS){
    fprintf(stderr, "connect: established connection\n");
  }

  return fd;
}

int net_listen(char *name, int port, int flags)
{
  int p, len, fd, se;
  char *ptr, *host, *copy;
  struct hostent *he;
  struct sockaddr_in sa;
  int value;

  p = 0;

  ptr = NULL;
  copy = NULL;
  host = NULL;

  if(name){
    ptr = strchr(name, ':');

    if(ptr != NULL){ /* has a colon */

      p = atoi(ptr + 1);

      if(ptr > name){ /* has a colon with something infront */

        len = ptr - name;

        copy = strdup(name);
        if(copy == NULL){
          if(flags & NETC_VERBOSE_ERRORS) fprintf(stderr, "listen: unable to duplicate string\n");
          errno = ENOMEM;
          return -1;
        }

        copy[len] = '\0';
        host = copy;
      }
    } else { /* no colon */
      p = atoi(name); 
      if(p > 0){ /* could be a port */
        if(strchr(name, '.')){ /* ports don't contain fractions, assume an IP */
          host = name;
          p = 0;
        }
      } else {
        host = name;
      }
    }
  }

  if(port > 0){
    p = port;
  }
#if 0
  if(port > 0xffff){
    port = port 
  }
#endif

  if(p == 0){
    if(!(flags & NETC_AUTO_PORT)){
      p = NETC_DEFAULT_PORT;
    }
  }

  if(host){
    if(inet_aton(host, &(sa.sin_addr)) == 0){
      he = gethostbyname(host);
      if((he == NULL) || (he->h_addrtype != AF_INET)){
        if(flags & NETC_VERBOSE_ERRORS) fprintf(stderr, "listen: unable to map %s to ipv4 address\n", host);
        if(copy){
          free(copy);
        }
        errno = EINVAL;
        return -1;
      }
      sa.sin_addr = *(struct in_addr *) he->h_addr;
    }
  } else {
    sa.sin_addr.s_addr = htonl(INADDR_ANY);
  }

  if(copy){
    free(copy);
  }

  sa.sin_port = htons(p);
  sa.sin_family = AF_INET;

  fd = socket(AF_INET, SOCK_STREAM, 0);
  if(fd < 0){
    if(flags & NETC_VERBOSE_ERRORS){
      se = errno;
      fprintf(stderr, "listen: unable to allocate socket: %s\n", strerror(errno));
      errno = se;
    }
    return -1;
  }

  /* slightly risky behaviour in order to gain some convenience */
  value = 1;
  setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &value, sizeof(value));
   
#ifndef MSG_NOSIGNAL
#ifdef SO_NOSIGPIPE
  value = 1;
  setsockopt(fd, SOL_SOCKET, SO_NOSIGPIPE, &value, sizeof(value));
#endif
#endif
   
  if(flags & NETC_VERBOSE_STATS){
    fprintf(stderr, "listen: about to bind %u\n", p);
  }

  len = sizeof(struct sockaddr_in);
  if(bind(fd, (struct sockaddr *)(&sa), len)){
    se = errno;
    close(fd);
    if(flags & NETC_VERBOSE_ERRORS) fprintf(stderr, "listen: bind to %u failed: %s\n", p, strerror(errno));
    errno = se;
    return -1;
  }

  if(listen(fd, 3)){
    se = errno;
    close(fd);
    if(flags & NETC_VERBOSE_ERRORS) fprintf(stderr, "listen: unable to listen on port %u: %s\n", p, strerror(errno));
    errno = se;
    return -1;
  }

  if(flags & NETC_VERBOSE_STATS){
    fprintf(stderr, "listen: ready for connections\n");
  }

  return fd;
}

#ifdef UNIT_TEST_NETC

int main(int argc, char **argv)
{
  int fd;
  unsigned int len;
  struct sockaddr_in sa;

  fprintf(stderr, "netc.c test\n");

  if(argc < 2){
    fprintf(stderr, "usage: %s host:port\n", argv[0]);
    return 1;
  }

  fd = net_listen(argv[1], (argc > 2) ? atoi(argv[2]) : 0, NETC_VERBOSE_ERRORS | NETC_VERBOSE_STATS | NETC_AUTO_PORT);
  if(fd < 0){
    fprintf(stderr, "%s: failed\n", argv[0]);
    return 1;
  }

  fprintf(stderr, "%s: ok\n", argv[0]);

  len = sizeof(struct sockaddr_in);
  if(getsockname(fd, (struct sockaddr *)&sa, &len) == 0){
    fprintf(stderr, "%s: actually bound port %d\n", argv[0], ntohs(sa.sin_port));
  }

  sleep(30);

  close(fd);

  return 0;
}

#endif
