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

#define CHUNK_SIZE       1988
#define SKARAB_PORT     30584
#define SEQUENCE_FIRST   0x10  
#define SEQUENCE_STRIDE  0x10  /* (N*STRIDE)+FIRST = initial sequence of board N */

#define MAX_PROBLEMS       10  /* try to deal with tings */

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
  struct timeval s_delta;
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

  unsigned int t_sent;
  unsigned int t_got;
  unsigned int t_weird;
  unsigned int t_late;
  unsigned int t_defer;

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

  char t_buffer[CHUNK_SIZE];
};

/*****************************************************************************/

volatile int run = 0;

/*****************************************************************************/

struct total *create_total()
{
  struct total *t;
  unsigned int i;

  t = malloc(sizeof(struct total));
  if(t == NULL){
    return NULL;
  }

  t->t_stall.tv_sec = 0;
  t->t_stall.tv_usec = 0;

  t->t_verbose = 0;

  t->t_sent = 0;
  t->t_got = 0;
  t->t_weird = 0;
  t->t_late = 0;
  t->t_defer = 0;

  t->t_fd = (-1);
  t->t_count = 0;
  t->t_vector = NULL;

  t->t_base = NULL;
  t->t_chunks = 0;
  t->t_length = 0;

  t->t_header.h_magic = htons(SKARAB_REQ);

# if 0
  t->t_header.h_sequence = 0;
  t->t_header.h_chunk = 0;
  t->t_header.h_total = 0;
#endif

  t->t_address.sin_family = AF_INET;
  /* t->t_address.sin_addr */
  t->t_address.sin_port = htons(SKARAB_PORT);

  t->t_io[0].iov_base = &(t->t_header);
  t->t_io[0].iov_len = 8;

  /* t->t_io[1].iov_base */
  t->t_io[1].iov_len = CHUNK_SIZE;

  t->t_message.msg_name       = &(t->t_address);
  t->t_message.msg_namelen    = sizeof(struct sockaddr_in);

  t->t_message.msg_iov        = t->t_io;
  t->t_message.msg_iovlen     = 2;

  t->t_message.msg_control    = NULL;
  t->t_message.msg_controllen = 0;

  t->t_message.msg_flags      = 0;

  for(i = 0; i < CHUNK_SIZE; i++){
    t->t_buffer[i] = i & 0xff;
  }

  return t;
}

int add_total(struct total *t, char *skarab)
{
  struct sockaddr_in address;
  struct skarab *s;

  if(net_address((struct sockaddr *)&address, skarab, SKARAB_PORT, 0) < 0){
    fprintf(stderr, "unable to add %s\n", skarab);
    return -1;
  }

  s = realloc(t->t_vector, sizeof(struct skarab) * (t->t_count + 1));
  if(s == NULL){
    fprintf(stderr, "unable to add entry number %u\n", t->t_count);
    return -1;
  }

  t->t_vector = s;
  s = &(t->t_vector[t->t_count]);
  t->t_count++;

  s->s_sequence = 0;

  s->s_chunk = -1; /* TODO: the extra do nothing packet should be made to go away */
  s->s_addr = address.sin_addr.s_addr;

  s->s_last.tv_sec = 0;
  s->s_last.tv_usec = 0;

  s->s_expire.tv_sec = 0;
  s->s_expire.tv_usec = 0;

  component_th(&(s->s_delta), INITIAL_TIMEOUT);

  return 0;
}

/*****************************************************************************/

static int compare_qsort(const void *a, const void *b)
{
  const struct skarab *alpha, *beta;

  alpha = a;
  beta = b;

  if(alpha->s_addr < beta->s_addr){
    return -1;
  }

  if(alpha->s_addr == beta->s_addr){
    return 0;
  }

  return 1;
}

/*****************************************************************************/

static int start_total(struct total *t, int verbose)
{
  int fd;
  unsigned int i, smear;
  struct skarab *s;
  struct timeval when, extra;

  t->t_verbose = verbose;

  if(t->t_fd >= 0){
    fprintf(stderr, "closing previous file descriptor\n");
    close(t->t_fd);
    t->t_fd = (-1);
  }

  if(t->t_count <= 0){
    fprintf(stderr, "need at least one device to talk to\n");
    return -1;
  }

  if(t->t_chunks <= 0){
    fprintf(stderr, "no data file given\n");
    return -1;
  }

#if 0
  sa.sin_family = AF_INET;
  sa.sin_addr.s_addr = htonl(INADDR_ANY);
  sa.sin_port = 0;
#endif

  fd = socket(AF_INET, SOCK_DGRAM, 0);
  if(fd < 0){
    fprintf(stderr, "unable to create socket: %s\n", strerror(errno));
    return -1;
  }

  t->t_fd = fd;

#ifdef DEBUG
  fprintf(stderr, "initialised network\n");
#endif

  gettimeofday(&when, NULL);
  t->t_begin.tv_sec  = when.tv_sec;
  t->t_begin.tv_usec = when.tv_usec;

  extra.tv_sec = 0;
  smear = (INITIAL_TIMEOUT * 1000) / t->t_count;
  if(smear <= 0){
    smear = 1;
  } else if(smear >= 1000000){
    smear = 999999;
  }
  extra.tv_usec = smear;

  for(i = 0; i < t->t_count; i++){
    s = &(t->t_vector[i]);

    s->s_sequence = SEQUENCE_FIRST + (i * SEQUENCE_STRIDE);

    s->s_expire.tv_sec  = when.tv_sec;
    s->s_expire.tv_usec = when.tv_usec;

    add_th(&when, &when, &extra);
  }

  qsort(t->t_vector, t->t_count, sizeof(struct skarab), &compare_qsort);

  return 0;
}

int open_total(struct total *t, char *name)
{
  struct stat st;
  int fd;

  fd = open(name, O_RDONLY);
  if(fd < 0){
    fprintf(stderr, "unable to open %s: %s\n", name, strerror(errno));
    return -1;
  }

  if(fstat(fd, &st) < 0){
    fprintf(stderr, "unable to stat %s: %s\n", name, strerror(errno));
    close(fd);
    return -1;
  }

  t->t_chunks = (st.st_size + CHUNK_SIZE - 1) / CHUNK_SIZE;
  t->t_length = st.st_size;

  if(t->t_verbose > 1){
    printf("file %s has %lu bytes or %d %u byte chunks\n", name, st.st_size, t->t_chunks, CHUNK_SIZE);
  }

  t->t_base = mmap(NULL, t->t_chunks * CHUNK_SIZE, PROT_READ, MAP_PRIVATE, fd, 0);
  if(t->t_base == MAP_FAILED){
    fprintf(stderr, "unable to map %s: %s\n", name, strerror(errno));
    close(fd);
    return -1;
  }

  if(t->t_verbose > 2){
    printf("mapped %s at %p\n", name, t->t_base);
  }

  t->t_header.h_total = htons(t->t_chunks);

  close(fd);

  return 0;
}

/*****************************************************************************/

static struct skarab *find_skarab(struct total *t, in_addr_t match)
{
  struct skarab key;

  key.s_addr = match;

  return bsearch(&key, t->t_vector, t->t_count, sizeof(struct skarab), &compare_qsort);
}

/*****************************************************************************/

static int perform_send(struct total *t, struct skarab *s)
{
  int wr, need;

  if(s->s_chunk >= t->t_chunks){
#ifdef DEBUG
    fprintf(stderr, "all done %d/%u\n", s->s_chunk, t->t_chunks);
#endif
    gettimeofday(&(s->s_expire), NULL);
    return 1;
  }

  s->s_sequence++;

  /* t->t_header.h_magic */
  t->t_header.h_sequence = htons(s->s_sequence);
  t->t_header.h_chunk = htons(s->s_chunk + 1);
  /* t->t_header.h_total */

#ifdef DEBUG
  fprintf(stderr, "sending chunk %d/%d\n", s->s_chunk, t->t_chunks);
#endif

  /* t->t_io[0].iov_base */
  if(s->s_chunk < 0){
    /* TODO: please retire the extra packet */
    t->t_io[1].iov_base = t->t_buffer;
  } else if ((s->s_chunk + 1) == t->t_chunks){
    need = t->t_length - (s->s_chunk * CHUNK_SIZE);
    memcpy(t->t_buffer, t->t_base + (s->s_chunk * CHUNK_SIZE), need);
    t->t_io[1].iov_base = t->t_buffer;
  } else {
    t->t_io[1].iov_base = t->t_base + (s->s_chunk * CHUNK_SIZE);
  }

  /* t->t_address.sin_family */
  t->t_address.sin_addr.s_addr = s->s_addr;
  /* t->t_address.sin_port */

  wr = sendmsg(t->t_fd, &(t->t_message), MSG_NOSIGNAL | MSG_DONTWAIT);

  if(wr < 0){
    switch(errno){
      case EAGAIN :
      case EINTR  :
        t->t_defer++;
        return 0;
      default :
        fprintf(stderr, "send failed with %s\n", strerror(errno));
        return -1;
    }
  }

  t->t_sent++;

  if(wr != (8 + CHUNK_SIZE)){
    fprintf(stderr, "unexpected send length %d\n", wr);
    return -1;
  }

  gettimeofday(&(s->s_last), NULL);

  add_th(&(s->s_expire), &(s->s_last), &(s->s_delta));

#ifdef DEBUG
  fprintf(stderr, "sent chunk %d/%d\n", s->s_chunk, t->t_chunks);
#endif

  return 0;
}

static int perform_index(struct total *t, unsigned int i)
{
  struct skarab *s;

  s = &(t->t_vector[i]);

  return perform_send(t, s);
}

static int perform_receive(struct total *t)
{
  int rr;
  struct sockaddr_in from;
  struct header answer;
  struct skarab *s;
  unsigned int len;
  struct timeval now;
  in_addr_t ip;
  uint16_t where, sequence;

  len = sizeof(struct sockaddr_in);
  rr = recvfrom(t->t_fd, &answer, sizeof(struct header), MSG_DONTWAIT, (struct sockaddr *)&from, &len);
  if(rr < 0){
    switch(errno){
      case EAGAIN :
      case EINTR  :
        t->t_defer++;
        return 0;
      default :
        fprintf(stderr, "receive failed with %s\n", strerror(errno));
        return -1;
    }
  }

  t->t_got++;

  gettimeofday(&now, NULL);

  ip = from.sin_addr.s_addr;

  if(rr != sizeof(struct header)){
    fprintf(stderr, "unexpected reply length %d from 0x%08x\n", rr, ip);
    t->t_weird++;
    return -1;
  }

  s = find_skarab(t, ip);
  if(s == NULL){
    fprintf(stderr, "got message random host 0x%08x\n", ip);
    t->t_weird++;
    return -1;
  }

  sequence = ntohs(answer.h_sequence);
  where    = ntohs(answer.h_chunk);

#ifdef DEBUG
  fprintf(stderr, "got reply from 0x%08x@%p, sequence=%x, chunk=%d\n", ip, s, sequence, where);
#endif

#ifdef CHECK
  if(ntohs(answer.h_magic) != SKARAB_ACK){
    fprintf(stderr, "bad reply code 0x%04x - expected 0x%04x\n", ntohs(answer.h_magic), SKARAB_ACK);
    t->t_weird++;
    return -1;
  }

  if(ntohs(answer.h_total) != 0){
    fprintf(stderr, "got error code 0x%04x from 0x%08x\n", ntohs(answer.h_total), ip);
    t->t_weird++;
    return -1;
  }
#endif

  if(where > (s->s_chunk + 1)){
    fprintf(stderr, "chunk 0x%04x from the future - expected 0x%04x\n", where, s->s_chunk + 1);
    t->t_weird++;
    return 0;
  }

  if(where < (s->s_chunk + 1)){
    fprintf(stderr, "stale chunk 0x%04x - expected 0x%04x\n", where, s->s_chunk + 1);
    /* wait a bit more ... */
    add_th(&(s->s_expire), &now, &(s->s_delta));
    t->t_late++;
    return 0;
  }

  if(sequence != s->s_sequence){
    fprintf(stderr, "mismatched sequence number 0x%04x - expected 0x%04x\n", ntohs(answer.h_sequence), s->s_sequence);
    /* wait a bit more ... otherwise other packet might not drain */
    add_th(&(s->s_expire), &now, &(s->s_delta));
    t->t_weird++;
    return 0;
  }

  s->s_chunk++;

#if 0
  sub_th(&(s->s_delta), &now, &(s->s_last)));
  /* TODO: loads of fudge factors ... */
#endif

  return perform_send(t, s);
}

/*****************************************************************************/

int complete_count(struct total *t)
{
  unsigned int i;
  struct skarab *s;
  int number;

  number = 0;

  for(i = 0; i < t->t_count; i++){
    s = &(t->t_vector[i]);

    if(s->s_chunk >= t->t_chunks){
      number++;
    }
  }

  return number;
}

/*****************************************************************************/

static void handle_signal(int s)
{
  switch(s){
    case SIGHUP :
      run = (-1);
      break;
    case SIGINT :
    case SIGTERM :
      run = 0;
      break;
  }
}


/*****************************************************************************/

static int bulk_send(struct total *t)
{
  struct skarab *s;
  struct timeval now, closer;
  unsigned int i;
  int result, total, finished;

  gettimeofday(&now, NULL);

#ifdef DEBUG
  if(sizeof(closer.tv_sec) != sizeof(long)){
    fprintf(stderr, "time field is an unexpected size\n");
    abort();
  }
#endif

  closer.tv_sec = LONG_MAX;
  total = 0;
  finished = 0;

  for(i = 0; i < t->t_count; i++){
    s = &(t->t_vector[i]);
    if(cmp_th(&now, &(s->s_expire)) >= 0){
      result = perform_index(t, i);
      if(result > 0){
        finished++;
      } else if(result < 0){
        total = result;
      }
    }
    if(cmp_th(&closer, &(s->s_expire)) > 0){
      closer.tv_sec  = s->s_expire.tv_sec;
      closer.tv_usec = s->s_expire.tv_usec;
    }
  }

  t->t_stall.tv_sec  = closer.tv_sec;
  t->t_stall.tv_usec = closer.tv_usec;

  if(finished >= t->t_count){
    return 1;
  }

  return total;
}

/*****************************************************************************/

void usage(char *name)
{
  printf("usage: %s -qhvf file [skarab]*\n", name);
  printf("-f file  BIN file to upload\n");
  printf("-q       quiet operation \n");
  printf("-v       more output\n");
  printf("-h       this help\n");
  printf("\n");
  printf("note: the list of skarabs is space delimited\n");
}

int main(int argc, char **argv)
{
  struct total *t;
  struct sigaction sag;
  fd_set fsr;
  int verbose, result, problems, completed;
  int i, j, c;
  char *app;
  struct timeval delta, now;
  unsigned int last;

  verbose = 2;
  app = argv[0];

//  int ctr;
//  printf("*&^*&^*&^*&^*^*&^*&^*&^*&^\n");
//  for(ctr=0; ctr<argc; ctr++){
//    printf("%i: %s\n", ctr, argv[ctr]);
//  }
//  printf("*&^*&^*&^*&^*^*&^*&^*&^*&^\n");

  verbose = 0;

  t = create_total();
  if(t == NULL){
    return EX_OSERR;
  }

  i = j = 1;
  while (i < argc) {
    if (argv[i][0] == '-') {
      c = argv[i][j];
      switch (c) {
        case 'h' :
          usage(argv[0]);
          return EX_OK;

        case 'v' :
          verbose++;
          j++;
          break;

        case 'q' :
          verbose = 0;
          j++;
          break;

        case 'f' :

          j++;
          if (argv[i][j] == '\0') {
            j = 0;
            i++;
          }

          if (i >= argc) {
            fprintf(stderr, "%s: usage: option -%c needs a parameter\n", app, c);
            return EX_USAGE;
          }

          switch(c){
            case 'f' :
              if(open_total(t, argv[i] + j) < 0){
                return EX_OSERR;
              }
              break;
          }

          i++;
          j = 1;
          break;

        case '-' :
          j++;
          break;

        case '\0':
          j = 1;
          i++;
          break;
        default:
          fprintf(stderr, "%s: usage: unknown option -%c\n", app, argv[i][j]);
          return EX_USAGE;
      }
    } else {
      if(add_total(t, argv[i])){
        return EX_SOFTWARE;
      }
      i++;
    }
  }

  sag.sa_handler = handle_signal;
  sigemptyset(&(sag.sa_mask));
  sag.sa_flags = SA_RESTART;

  sigaction(SIGINT, &sag, NULL);
  sigaction(SIGHUP, &sag, NULL);
  sigaction(SIGTERM, &sag, NULL);

  if(start_total(t, verbose)){
    fprintf(stderr, "%s: initialisation failed\n", app);
    return EX_SOFTWARE;
  }

  if(verbose > 1){
    printf("attempting to upload to %u skarabs\n", t->t_count);
  }

  problems = 0;
  last = 0;

  for(run = 1; run > 0; ){
    
    result = bulk_send(t);
    if(result > 0){
      break;
    }
    if(result < 0){
      problems++;
      if(problems > MAX_PROBLEMS){
        fprintf(stderr, "%s: too many problems, giving up\n", app);
        return EX_SOFTWARE;
      }
    }

    FD_ZERO(&fsr);
    FD_SET(t->t_fd, &fsr);

    gettimeofday(&now, NULL);
    if(verbose > 0){
      if(last != now.tv_sec){
        printf("\rTX=%7u", t->t_sent);
        fflush(stdout);
        last = now.tv_sec;
      }
    }

    sub_th(&delta, &(t->t_stall), &now);

    result = select(t->t_fd + 1, &fsr, NULL, NULL, &delta);
    if(result < 0){
      switch(errno){
        case EAGAIN : 
        case EINTR : 
          break;
        default :
          problems++;
          break;
      }
    }

    if(result > 0){
      result = perform_receive(t);
      if(result < 0){
        problems++;
      }
    }

  }

  if(verbose > 0){
    printf("\r");
  }

  gettimeofday(&now, NULL);

  sub_th(&delta, &now, &(t->t_begin));
  completed = complete_count(t);

  if(verbose > 0){
    if(verbose > 1){
      printf("total skarabs: %u\n", t->t_count);
      printf("completed uploads: %d\n", completed);
      printf("significant errors: %d\n", problems);
      printf("required block operations: %u\n", t->t_count * (t->t_chunks + 1));
      printf("packets sent: %u\n", t->t_sent);
      printf("packets received: %u\n", t->t_got);
      printf("unusual received packets: %u\n", t->t_weird);
      printf("late received packets: %u\n", t->t_late);
      printf("interruptions and stalls: %u\n", t->t_defer);
      printf("total time: %lu.%06lus\n", delta.tv_sec, delta.tv_usec);
      printf("send data rate: %.3fMb/s\n", ((double)(t->t_sent) * (CHUNK_SIZE + sizeof(struct header))) / ((delta.tv_sec * 1000000) + delta.tv_usec));
    } else {
      printf("programmed %d of %u skarabs in %lu.%06lus with %d problems\n", completed, t->t_count, delta.tv_sec, delta.tv_usec, problems);
    }
  }

  return EX_OK;
}

