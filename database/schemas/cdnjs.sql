-- MySQL dump 10.16  Distrib 10.3.8-MariaDB, for Linux (x86_64)
--
-- Host: localhost    Database: extensions
-- ------------------------------------------------------
-- Server version	10.3.8-MariaDB-log

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `cdnjs`
--

DROP TABLE IF EXISTS `cdnjs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `cdnjs` (
  `path` varchar(512) COLLATE utf8mb4_unicode_ci NOT NULL,
  `typ` enum('AS_IS','NORMALIZED','DECOMPRESSED','DECOMPRESSED_NORMALIZED') COLLATE utf8mb4_unicode_ci NOT NULL,
  `md5` varbinary(16) NOT NULL,
  `filename` varchar(253) /*!100301 COMPRESSED*/ COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `sha1` varbinary(20) DEFAULT NULL,
  `sha256` varbinary(32) DEFAULT NULL,
  `simhash` varbinary(64) DEFAULT NULL,
  `size` bigint(20) DEFAULT NULL,
  `loc` bigint(20) DEFAULT NULL,
  `description` text /*!100301 COMPRESSED*/ COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `encoding` text /*!100301 COMPRESSED*/ COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mimetype` varchar(126) /*!100301 COMPRESSED*/ COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `add_date` datetime(6) NULL DEFAULT NULL,
  `library` varchar(254) /*!100301 COMPRESSED*/ COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `version` varchar(30) /*!100301 COMPRESSED*/ COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `mimetype_detail` text /*!100301 COMPRESSED*/ COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_modified` datetime NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`path`,`typ`),
  KEY `cdnjs_md5_typ` (`md5`,`typ`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci `PAGE_COMPRESSED`='ON';
/*!40101 SET character_set_client = @saved_cs_client */;

/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2018-08-09 12:31:29
