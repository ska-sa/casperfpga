/* GPLed time comparison code grabbed from libloop */

#include <stdio.h>
#include <stdlib.h>
#include <sys/time.h>
#include <sys/types.h>

#include <th.h>

int from_string_th(struct timeval *tv, char *string)
{
  char *end, *ptr;
  unsigned long v[2]; /* keep tv unchanged in case of parsing failure */
  int digits;

  if(string == NULL){
    return -1;
  }

  ptr = string;

  v[0] = strtoul(ptr, &end, 10);
  switch(*end){
    case ' '  :
    case '\n' :
    case '\r' : 
    case '\t' :
      /* WARNING: above chars mean string doesn't only contain a number */
    case '\0' :
      if(end == ptr){ /* empty string, fail */
        return -1;
      }

      /* had to be something valid, no fractional part */
      tv->tv_sec = v[0];
      tv->tv_usec = 0;
      return 0;

    case '.' :
      /* move on to fractional handling logic, everything else fails */
      ptr = end + 1;
      break;

    default :
      return -1;
  }

  v[1] = strtoul(ptr, &end, 10);
  switch(*end){
    case ' '  :
    case '\n' :
    case '\r' : 
    case '\t' :
      /* WARNING: above chars mean string doesn't only contain a number */
    case '\0' :
      if(end == ptr){ /* empty string, fail */
        return -1;
      }

      /* this is rather lame, but avoids floats. Should actually manually parse the string */
      digits = end - ptr;
      if(digits < 0){
        return -1;
      }

      if(digits > 10){ /* integer overflow on 32 bits */
        return -1;
      }

      while(digits > 6){
        v[1] = v[1] / 10;
        digits--;
      }
      while(digits < 6){
        v[1] = v[1] * 10;
        digits++;
      }
      
      tv->tv_sec = v[0];
      tv->tv_usec = v[1];
      return 0;

    default :
      return -1;
  }

}

void component_th(struct timeval *result, unsigned int ms)
{
  result->tv_sec  = ms / 1000;
  result->tv_usec = (ms % 1000) * 1000;
#ifdef DEBUG
  fprintf(stderr, "component time: %ums -> %lu.%06lds\n", ms, result->tv_sec, result->tv_usec);
#endif
}

int cmp_th(struct timeval *alpha, struct timeval *beta)
{
  if(alpha->tv_sec < beta->tv_sec){
    return -1;
  }

  if(alpha->tv_sec > beta->tv_sec){
    return 1;
  }

  if(alpha->tv_usec < beta->tv_usec){
    return -1;
  }

  if(alpha->tv_usec > beta->tv_usec){
    return 1;
  }

  return 0;
}

int add_th(struct timeval *sigma, struct timeval *alpha, struct timeval *beta)
{
  if(alpha->tv_usec + beta->tv_usec >= 1000000){
    sigma->tv_sec = alpha->tv_sec + beta->tv_sec + 1;
    sigma->tv_usec = (alpha->tv_usec + beta->tv_usec) - 1000000;
  } else {
    sigma->tv_sec = alpha->tv_sec + beta->tv_sec;
    sigma->tv_usec = alpha->tv_usec + beta->tv_usec;
  }
  return 0;
}

int sub_th(struct timeval *delta, struct timeval *alpha, struct timeval *beta)
{
  if(alpha->tv_usec < beta->tv_usec){
    if(alpha->tv_sec <= beta->tv_sec){
      delta->tv_sec  = 0;
      delta->tv_usec = 0;
      return -1;
    }
    delta->tv_sec  = alpha->tv_sec - (beta->tv_sec + 1);
    delta->tv_usec = (1000000 + alpha->tv_usec) - beta->tv_usec;
  } else {
    if(alpha->tv_sec < beta->tv_sec){
      delta->tv_sec  = 0;
      delta->tv_usec = 0;
      return -1;
    }
    delta->tv_sec  = alpha->tv_sec  - beta->tv_sec;
    delta->tv_usec = alpha->tv_usec - beta->tv_usec;
  }
#ifdef DEBUG
  if(delta->tv_usec >= 1000000){
    fprintf(stderr, "major logic failure: %lu.%06lu-%lu.%06lu yields %lu.%06lu\n", alpha->tv_sec, alpha->tv_usec, beta->tv_sec, beta->tv_usec, delta->tv_sec, delta->tv_usec);
    abort();
  }
#endif
  return 0;
}
