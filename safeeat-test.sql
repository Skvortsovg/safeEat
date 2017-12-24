-- MySQL Script generated by MySQL Workbench
-- Tue Dec 19 01:17:31 2017
-- Model: New Model    Version: 1.0
-- MySQL Workbench Forward Engineering

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='TRADITIONAL,ALLOW_INVALID_DATES';

-- -----------------------------------------------------
-- Schema safeeat
-- -----------------------------------------------------
DROP SCHEMA IF EXISTS `safeeat` ;

-- -----------------------------------------------------
-- Schema safeeat
-- -----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS `safeeat` DEFAULT CHARACTER SET utf8 ;
USE `safeeat` ;

-- -----------------------------------------------------
-- Table `safeeat`.`ingredients`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `safeeat`.`ingredients` ;

CREATE TABLE IF NOT EXISTS `safeeat`.`ingredients` (
  `id` INT(10) UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `proteins` DOUBLE NOT NULL,
  `fats` DOUBLE NOT NULL,
  `carbohydrates` DOUBLE NOT NULL,
  `calories` DOUBLE NOT NULL,
  `measure` VARCHAR(5) NOT NULL,
  `type` VARCHAR(255) NOT NULL,
  PRIMARY KEY (`id`))
ENGINE = InnoDB;

CREATE UNIQUE INDEX `id_UNIQUE` ON `safeeat`.`ingredients` (`id` ASC);


-- -----------------------------------------------------
-- Table `safeeat`.`dishes`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `safeeat`.`dishes` ;

CREATE TABLE IF NOT EXISTS `safeeat`.`dishes` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `Name` VARCHAR(255) NOT NULL,
  `description` LONGTEXT NULL,
  PRIMARY KEY (`id`))
ENGINE = InnoDB;

CREATE UNIQUE INDEX `id_UNIQUE` ON `safeeat`.`dishes` (`id` ASC);

CREATE UNIQUE INDEX `Name_UNIQUE` ON `safeeat`.`dishes` (`Name` ASC);


-- -----------------------------------------------------
-- Table `safeeat`.`users`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `safeeat`.`users` ;

CREATE TABLE IF NOT EXISTS `safeeat`.`users` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `height` DOUBLE NOT NULL,
  `weight` DOUBLE NOT NULL,
  `sex` INT NOT NULL,
  `calories` DOUBLE NOT NULL,
  `proteins` DOUBLE NOT NULL,
  `fats` DOUBLE NOT NULL,
  `carbohydrates` DOUBLE NOT NULL,
  `birthyear` INT NOT NULL,
  PRIMARY KEY (`id`))
ENGINE = InnoDB;

CREATE UNIQUE INDEX `iduser_UNIQUE` ON `safeeat`.`users` (`id` ASC);

CREATE UNIQUE INDEX `name_UNIQUE` ON `safeeat`.`users` (`name` ASC);


-- -----------------------------------------------------
-- Table `safeeat`.`norm`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `safeeat`.`norm` ;

CREATE TABLE IF NOT EXISTS `safeeat`.`norm` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `calories` DOUBLE NOT NULL,
  `proteins` DOUBLE NOT NULL,
  `fats` DOUBLE NOT NULL,
  `carbohydrates` DOUBLE NOT NULL,
  `user_id` INT UNSIGNED NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `id`
    FOREIGN KEY (`user_id`)
    REFERENCES `safeeat`.`users` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;

CREATE UNIQUE INDEX `id_UNIQUE` ON `safeeat`.`norm` (`id` ASC);

CREATE UNIQUE INDEX `user_id_UNIQUE` ON `safeeat`.`norm` (`user_id` ASC);


-- -----------------------------------------------------
-- Table `safeeat`.`d_i`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `safeeat`.`d_i` ;

CREATE TABLE IF NOT EXISTS `safeeat`.`d_i` (
  `id` INT UNSIGNED NOT NULL AUTO_INCREMENT,
  `dishes_id` INT UNSIGNED NOT NULL,
  `ingredients_id` INT UNSIGNED NOT NULL,
  `ammount` INT NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk1`
    FOREIGN KEY (`dishes_id`)
    REFERENCES `safeeat`.`dishes` (`id`)
    ON DELETE CASCADE
    ON UPDATE NO ACTION,
  CONSTRAINT `fk2`
    FOREIGN KEY (`ingredients_id`)
    REFERENCES `safeeat`.`ingredients` (`id`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;

CREATE UNIQUE INDEX `dishes_id_UNIQUE` ON `safeeat`.`d_i` (`dishes_id` ASC);

CREATE UNIQUE INDEX `ingredients_id_UNIQUE` ON `safeeat`.`d_i` (`ingredients_id` ASC);

CREATE UNIQUE INDEX `id_UNIQUE` ON `safeeat`.`d_i` (`id` ASC);


-- -----------------------------------------------------
-- Table `safeeat`.`archive`
-- -----------------------------------------------------
DROP TABLE IF EXISTS `safeeat`.`archive` ;

CREATE TABLE IF NOT EXISTS `safeeat`.`archive` (
  `id` INT(10) UNSIGNED NOT NULL,
  `calories` DOUBLE NOT NULL,
  `proteins` DOUBLE NOT NULL,
  `fats` DOUBLE NOT NULL,
  `carbohydrates` DOUBLE NOT NULL,
  `user_id` INT UNSIGNED NOT NULL,
  `date` DATE NOT NULL,
  `goal` INT(11) NOT NULL,
  `lifestyle` INT(11) NOT NULL,
  PRIMARY KEY (`id`),
  CONSTRAINT `user_id`
    FOREIGN KEY (`user_id`)
    REFERENCES `safeeat`.`users` (`id`)
    ON DELETE CASCADE
    ON UPDATE CASCADE)
ENGINE = InnoDB;

CREATE UNIQUE INDEX `id_UNIQUE` ON `safeeat`.`archive` (`id` ASC);

CREATE UNIQUE INDEX `user_id_UNIQUE` ON `safeeat`.`archive` (`user_id` ASC);

GRANT ALL ON `safeeat`.* TO 'admin';

SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;