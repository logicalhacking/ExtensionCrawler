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
-- Table structure for table `extension`
--

DROP TABLE IF EXISTS `extension`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8 */;
CREATE TABLE `extension` (
  `extid` varchar(32) COLLATE utf8mb4_unicode_ci NOT NULL,
  `date` timestamp(6) NOT NULL,
  `name` text /*!100301 COMPRESSED*/ COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `version` text /*!100301 COMPRESSED*/ COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `description` text /*!100301 COMPRESSED*/ COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `downloads` int(11) DEFAULT NULL,
  `rating` double DEFAULT NULL,
  `ratingcount` int(11) DEFAULT NULL,
  `fulldescription` text /*!100301 COMPRESSED*/ COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `offeredby` text /*!100301 COMPRESSED*/ COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `developer` text /*!100301 COMPRESSED*/ COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `itemcategory` text /*!100301 COMPRESSED*/ COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `crx_etag` varchar(44) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `lastupdated` text /*!100301 COMPRESSED*/ COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `last_modified` timestamp NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  PRIMARY KEY (`extid`,`date`) KEY_BLOCK_SIZE=8,
  KEY `extension_crx_etag` (`crx_etag`),
  KEY `extension_date` (`date`),
  KEY `extension_date_extid` (`date`,`extid`),
  KEY `extension_extid_crx_etag` (`extid`,`crx_etag`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci `PAGE_COMPRESSED`='ON';
/*!40101 SET character_set_client = @saved_cs_client */;

/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2018-08-09 12:31:29
