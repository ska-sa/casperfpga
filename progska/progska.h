/* Released under the GNU GPLv3 - see COPYING */
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <errno.h>
#include <unistd.h>
#include <fcntl.h>
#include <sysexits.h>
#include <signal.h>
#include <stdint.h>
#include <limits.h>

#include <sys/mman.h>
#include <sys/stat.h>
#include <sys/select.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/types.h>

#include <netinet/in.h>
#include <arpa/inet.h>

#include <netc.h>
#include <th.h>

#define CHECK  /* paranoia */

#define MAX_CHUNK        9000
#define CHUNK_SIZE       1988
#define SKARAB_PORT     30584
#define SEQUENCE_FIRST   0x10
#define SEQUENCE_STRIDE  0x10  /* (N*STRIDE)+FIRST = initial sequence of board N */

#define MAX_PROBLEMS       10  /* try to deal with tings */
#define MAX_TIMEOUTS       50  /* */

#define SKARAB_REQ 0x0051  /* gets htons'ed */
#define SKARAB_ACK 0x0052  /* gets htons'ed */

#define INITIAL_TIMEOUT 20 /* in ms */

struct skarab
{
  uint16_t s_sequence;
  int s_chunk;
  in_addr_t s_addr;
  struct timeval s_last;
  struct timeval s_expire;
#if 0
  struct timeval s_delta;
#endif
};

struct header{
  uint16_t h_magic;
  uint16_t h_sequence;
  uint16_t h_chunk;
  uint16_t h_total;
} __attribute__ ((packed));

struct total{
  struct timeval t_begin;
  struct timeval t_stall;
  struct timeval t_interval;

  unsigned int t_sent;
  unsigned int t_got;
  unsigned int t_weird;
  unsigned int t_late;
  unsigned int t_future;
  unsigned int t_alien;
  unsigned int t_misfit;
  unsigned int t_defer;
  unsigned int t_timeout;

  unsigned int t_chunksize;

  unsigned int t_burst;

  int t_verbose;

  int t_fd;
  unsigned int t_count;
  struct skarab *t_vector;

  char *t_base;
  int t_chunks;
  unsigned int t_length;

  struct header t_header;

  struct iovec t_io[2];
  struct sockaddr_in t_address;

  struct msghdr t_message;

  char t_buffer[MAX_CHUNK];
};

struct total *create_total();
int update_chunksize(struct total *t, unsigned int chunksize);
void destroy_total(struct total *t);
int add_total(struct total *t, char *skarab);
static int compare_qsort(const void *a, const void *b);
static int start_total(struct total *t, int verbose);
int open_total(struct total *t, char *name);
static struct skarab *find_skarab(struct total *t, in_addr_t match);
static int perform_send(struct total *t, struct skarab *s);
static int perform_index(struct total *t, unsigned int i);
static int perform_receive(struct total *t);
int complete_count(struct total *t);
static void handle_signal(int s);
static int bulk_send(struct total *t);
void usage(char *name);
int main(int argc, char **argv);
